"""
FastAPI Backend Application for JA Assure AI Marketing Agent.
Exposes REST endpoints for generation, compliance checking, human review,
feedback-driven regeneration, lead scoring, and rejection-rate analytics.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.gemini_service import gemini_service
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from backend.agents.lead_agent import lead_agent
from backend.services import analytics_service
from backend import models, schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ja_assure.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is created and migrated on server boot."""
    init_db()
    logger.info("JA Assure database initialized and migrated.")
    yield


app = FastAPI(
    title="JA Assure AI Marketing Agent API",
    description="Agentic marketing engine for regulated InsurTech with compliance gating and human-in-the-loop feedback learning.",
    version="1.1.0",
    lifespan=lifespan,
)

# Enable CORS for local Streamlit dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from backend.services.llm_service import llm_service
from backend.knowledge.vector_store import vector_store
from backend.knowledge.pdf_pipeline import pdf_pipeline
from backend.agents.research_agent import competitor_research_agent

# =====================================================================
# Health & Status Endpoint
# =====================================================================

@app.get("/health", summary="System Health & LLM Status")
def health_check() -> Dict[str, Any]:
    """Check API health, database readiness, and LLM configuration status."""
    llm_status = llm_service.check_health()
    vector_stats = vector_store.get_company_knowledge_stats()
    return {
        "status": "healthy",
        "service": "JA Assure AI Marketing Intelligence & Risk Agent",
        "llm": llm_status,
        "knowledge_stats": vector_stats,
    }


# =====================================================================
# Content Generation & Compliance Endpoints
# =====================================================================

@app.post(
    "/content/research",
    response_model=schemas.ResearchResponse,
    summary="Research Official JA Assure Knowledge & Competitor Contrast",
)
def research_knowledge(payload: schemas.ResearchRequest) -> Dict[str, Any]:
    """
    Retrieve grounded research summary and official sources from JA Assure Resources
    with competitive contrast analysis and optional live research.
    """
    return research_agent.research(
        brand=payload.brand,
        topic=payload.topic,
        product=payload.product,
        competitor_list=payload.competitor_list,
    )


@app.post(
    "/content/generate",
    response_model=schemas.ContentItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Content with Compliance Gate",
)
def generate_content(payload: schemas.ContentGenerateRequest) -> Dict[str, Any]:
    """
    Generate marketing copy for a brand and platform.
    Automatically retrieves recent human feedback for few-shot prompt injection.
    Runs compliance check against brand rubric and stores item as 'pending' with generation metadata.
    """
    try:
        # 1. Generate content via Content Agent (grounded in JA Assure knowledge)
        generated = content_agent.generate_content(
            topic=payload.topic,
            brand=payload.brand,
            product=payload.product,
            platform=payload.platform,
            content_type=payload.content_type,
            rag_context=payload.research_context,
            additional_instruction=payload.additional_instruction,
            force_trigger_flaw=bool(payload.force_trigger_flaw),
            cycle=payload.cycle,
            allow_offline_fallback=bool(payload.allow_offline_fallback),
        )

        # 2. Evaluate with Compliance Agent (Stage 2 of Two-Stage Pipeline: checks claim grounding)
        compliance_verdict = compliance_agent.check(
            content=generated["content"],
            brand=payload.brand,
            claim_grounding=generated.get("claim_grounding"),
        )

        # 3. Store in SQLite with initial status='pending' (Human approval mandatory)
        saved_item = models.insert_content(
            brand=payload.brand,
            platform=payload.platform,
            content_type=payload.content_type,
            topic=payload.topic,
            product=generated.get("product"),
            content=generated["content"],
            compliance_result=compliance_verdict,
            cycle=payload.cycle,
            fixed_issue=generated.get("fixed_issue"),
            sources=generated.get("sources"),
            generation_mode=generated.get("generation_mode", "offline"),
            provider=generated.get("provider", "offline"),
            model=generated.get("model", "offline-engine"),
            prompt_version=generated.get("prompt_version", "1.0"),
            knowledge_source_ids=generated.get("knowledge_source_ids"),
            feedback_ids=generated.get("feedback_ids"),
            generation_metadata=generated.get("generation_metadata"),
            risk_level=compliance_verdict.get("risk_level", "LOW"),
            risk_score=compliance_verdict.get("risk_score", 0.0),
            status="pending",
        )

        # Attach ephemeral fields for immediate response
        saved_item["retrieved_sources"] = generated.get("retrieved_sources") or []
        saved_item["feedback_context_ids"] = generated.get("feedback_context_ids") or []
        saved_item["provider"] = generated.get("provider")
        saved_item["claim_grounding"] = generated.get("claim_grounding") or []
        saved_item["claims_used"] = generated.get("claims_used") or []
        saved_item["uncertain_claims"] = generated.get("uncertain_claims") or []
        saved_item["feedback_applied"] = generated.get("feedback_applied") or []
        saved_item["variant_id"] = generated.get("variant_id")
        saved_item["variants"] = generated.get("variants") or []

        return saved_item

    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error generating marketing content")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/content/{content_id}/check",
    response_model=schemas.ComplianceResult,
    summary="Re-run Compliance Gate on Content Item",
)
def check_content_compliance(content_id: int) -> Dict[str, Any]:
    """Re-evaluate an existing content item against its brand's compliance rubric."""
    item = models.get_content_by_id(content_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")

    verdict = compliance_agent.check(
        content=item["content"],
        brand=item["brand"],
    )
    models.update_compliance_result(content_id, verdict)
    return verdict


# =====================================================================
# Content Queue Management Endpoints
# =====================================================================

@app.get(
    "/content/pending",
    response_model=List[schemas.ContentItemResponse],
    summary="List Content Awaiting Human Review",
)
def get_pending_content(brand: Optional[str] = Query(None, description="Optional brand filter: Jade or DoctorShield")) -> List[Dict[str, Any]]:
    """Retrieve all content assets awaiting human approval."""
    return models.list_pending_content(brand=brand)


@app.get(
    "/content/approved",
    response_model=List[schemas.ContentItemResponse],
    summary="List Approved / Scheduled Marketing Content",
)
def get_approved_content(brand: Optional[str] = Query(None, description="Optional brand filter")) -> List[Dict[str, Any]]:
    """Retrieve approved and scheduled assets ready for social scheduling."""
    return models.list_approved_content(brand=brand)


@app.get(
    "/content/{content_id}",
    response_model=schemas.ContentItemResponse,
    summary="Get Content Item by ID",
)
def get_content_item(content_id: int) -> Dict[str, Any]:
    """Fetch a single content asset by its database ID."""
    item = models.get_content_by_id(content_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")
    return item


# =====================================================================
# Human-in-the-Loop Governance Endpoints
# =====================================================================

@app.post(
    "/content/{content_id}/approve",
    response_model=schemas.ContentItemResponse,
    summary="Human Approve Marketing Content",
)
def approve_content_item(content_id: int) -> Dict[str, Any]:
    """
    Human reviewer signs off on compliant content.
    Enforces strict state machine: content MUST be in pending state AND compliance status MUST be 'pass'.
    """
    try:
        updated = models.approve_content(content_id)
        return updated
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/content/{content_id}/reject",
    response_model=schemas.ContentItemResponse,
    summary="Reject Content with Feedback Note",
)
def reject_content_item(content_id: int, payload: schemas.RejectRequest) -> Dict[str, Any]:
    """
    Human reviewer rejects content and records feedback tag, note, and structured fields.
    Feedback is stored immutably and embedded in ChromaDB to instruct future generations.
    """
    try:
        updated = models.reject_content(
            content_id=content_id,
            tag=payload.tag,
            note=payload.note,
            issue_type=payload.issue_type,
            corrected_content=payload.corrected_content,
            risk_score=payload.risk_score,
            compliance_rule=payload.compliance_rule,
        )
        return updated
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/content/{content_id}/edit",
    response_model=schemas.ContentItemResponse,
    summary="Human Edit Marketing Content",
)
def edit_content_item(content_id: int, payload: schemas.EditRequest) -> Dict[str, Any]:
    """
    Human reviewer directly modifies content copy.
    GOVERNANCE: Re-checks compliance and resets status to 'pending' requiring fresh human approval.
    """
    try:
        item = models.get_content_by_id(content_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")

        new_compliance = compliance_agent.check(content=payload.edited_content, brand=item["brand"])

        updated = models.edit_content(
            content_id=content_id,
            edited_content=payload.edited_content,
            tag=payload.tag,
            note=payload.note,
            issue_type=payload.issue_type,
            compliance_rule=payload.compliance_rule,
            compliance_result=new_compliance,
        )
        return updated
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error in edit_content_item: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/content/{content_id}/schedule",
    response_model=schemas.ContentItemResponse,
    summary="Schedule Content for Publishing",
)
def schedule_content_item(content_id: int) -> Dict[str, Any]:
    """
    Transition content to 'scheduled' state.
    Enforces security rule: Can ONLY be scheduled if it was previously APPROVED.
    """
    try:
        updated = models.schedule_content(content_id)
        return updated
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# =====================================================================
# Closed-Loop Feedback & Regeneration Endpoints
# =====================================================================

@app.post(
    "/content/{content_id}/regenerate",
    response_model=schemas.ContentItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate Content with Human Feedback Loop",
)
def regenerate_content_item(
    content_id: int,
    payload: Optional[schemas.RegenerateRequest] = None,
) -> Dict[str, Any]:
    """
    Regenerates improved content for a rejected or edited item:
    1. Preserves original topic, brand, and platform from parent record.
    2. Pulls recent feedback for the brand (including the latest rejection reason).
    3. Forwards additional_instruction and feedback into the Content Agent prompt.
    4. Generates an improved version that explicitly fixes the flagged issue.
    5. Runs the Compliance Agent again.
    6. Stores new version linking parent_id = original content_id.
    """
    parent = models.get_content_by_id(content_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")

    try:
        # Retrieve recent feedback for this brand
        recent_feedback = feedback_agent.get_recent_feedback(brand=parent["brand"], n=5)

        # PRESERVE ORIGINAL TOPIC (Critical Fix Phase 6)
        original_topic = parent.get("topic") or (
            "Safeguarding multi-generational jewellery wealth and heirlooms"
            if parent["brand"] == "Jade"
            else "Clinical malpractice litigation risk and disciplinary defense"
        )

        additional_inst = payload.additional_instruction if payload else None

        # Ground in official JA Assure knowledge for original topic
        research_context = research_agent.research(brand=parent["brand"], topic=original_topic)

        # Generate new variant with original topic and additional instructions
        generated = content_agent.generate(
            topic=original_topic,
            brand=parent["brand"],
            platform=parent["platform"],
            content_type=parent["content_type"],
            research_context=research_context,
            past_corrections=recent_feedback,
            additional_instruction=additional_inst,
            force_trigger_flaw=False,  # Feedback loop resolves the flaw
            cycle=parent.get("cycle", 1) + 1,
        )

        # Re-run Compliance check (Stage 2: evaluate claim grounding)
        new_compliance = compliance_agent.check(
            content=generated["content"],
            brand=parent["brand"],
            claim_grounding=generated.get("claim_grounding"),
        )

        # Determine fixed issue description
        fixed_issue_desc = "Resolved compliance violation using reviewer feedback."
        if recent_feedback:
            fixed_issue_desc = f"Corrected: [{recent_feedback[0]['tag']}] {recent_feedback[0]['note']}"
        if additional_inst:
            fixed_issue_desc += f" (Instruction: {additional_inst})"

        # Save new variant linked to parent
        new_item = models.insert_content(
            brand=parent["brand"],
            platform=parent["platform"],
            content_type=parent["content_type"],
            topic=original_topic,
            content=generated["content"],
            compliance_result=new_compliance,
            cycle=parent.get("cycle", 1) + 1,
            parent_id=parent["id"],
            fixed_issue=fixed_issue_desc,
            sources=generated.get("sources") or parent.get("sources"),
            generation_mode=generated.get("generation_mode", "offline"),
            model=generated.get("model", "offline-engine"),
            prompt_version=generated.get("prompt_version", "1.0"),
            knowledge_source_ids=generated.get("knowledge_source_ids"),
            feedback_ids=generated.get("feedback_ids"),
            generation_metadata=generated.get("generation_metadata"),
            status="pending",
        )

        new_item["claim_grounding"] = generated.get("claim_grounding") or []
        new_item["claims_used"] = generated.get("claims_used") or []
        new_item["uncertain_claims"] = generated.get("uncertain_claims") or []
        new_item["feedback_applied"] = generated.get("feedback_applied") or []

        return new_item

    except Exception as exc:
        logger.exception(f"Failed to regenerate content for ID {content_id}")
        raise HTTPException(status_code=500, detail=str(exc))


# =====================================================================
# Feedback & Learning Analytics Endpoints
# =====================================================================

@app.get(
    "/feedback/recent",
    response_model=List[schemas.FeedbackItemResponse],
    summary="Get Recent Reviewer Feedback",
)
def get_recent_feedback_endpoint(
    brand: str = Query("Jade", description="Brand name: Jade or DoctorShield"),
    n: int = Query(5, ge=1, le=20, description="Number of feedback items to retrieve"),
) -> List[Dict[str, Any]]:
    """Retrieve the last N human feedback items for prompt injection or review."""
    return feedback_agent.get_recent_feedback(brand=brand, n=n)


@app.get(
    "/analytics/rejection-rate",
    response_model=schemas.RejectionRateResponse,
    summary="Get Rejection Rate by Generation Cycle",
)
def get_rejection_rate_stats() -> Dict[str, Any]:
    """Retrieve empirical proof of learning across generation cycles."""
    return feedback_agent.get_rejection_rate_analytics()


@app.get(
    "/analytics/dashboard",
    summary="Centralized Operational Dashboard KPIs",
)
def get_dashboard_metrics_endpoint() -> Dict[str, Any]:
    """Derive all operational metrics directly from SQLite database."""
    return analytics_service.get_dashboard_metrics()


@app.get(
    "/analytics/trends",
    summary="Cycle Trend Deltas & Learning Rate",
)
def get_trend_metrics_endpoint() -> Dict[str, Any]:
    """Retrieve trend deltas between latest and prior review cycles."""
    return analytics_service.get_trend_metrics()


@app.get(
    "/analytics/before-after",
    response_model=List[schemas.BeforeAfterComparison],
    summary="Before / After Regeneration Showcases",
)
def get_before_after_showcases(
    brand: Optional[str] = Query(None, description="Optional brand filter"),
    limit: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Retrieve paired Before (rejected) and After (regenerated) content assets."""
    return models.get_before_after_pairs(brand=brand, limit=limit)


# =====================================================================
# Leads Management Endpoints
# =====================================================================

@app.get(
    "/leads",
    response_model=List[schemas.LeadItemResponse],
    summary="List InsurTech Prospect Leads",
)
def get_leads_list(
    vertical: Optional[str] = Query(None, description="Filter by vertical: Jewellers, Clinics, SMEs, Couriers"),
    region: Optional[str] = Query(None, description="Filter by operating region"),
) -> List[Dict[str, Any]]:
    """Retrieve prospective leads ranked by fit score."""
    return models.list_leads(vertical=vertical, region=region)


@app.post(
    "/leads",
    response_model=schemas.LeadItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create InsurTech Lead",
)
def create_lead(payload: schemas.LeadCreateRequest) -> Dict[str, Any]:
    """Record a prospective InsurTech client lead with fit score."""
    new_lead = models.insert_lead(
        name=payload.name,
        contact=payload.contact,
        vertical=payload.vertical,
        region=payload.region,
        fit_score=payload.fit_score,
        outreach_draft=payload.outreach_draft,
        source=payload.source,
        source_url=payload.source_url,
        scoring_breakdown=payload.scoring_breakdown,
    )
    return new_lead


@app.post(
    "/leads/discover",
    response_model=List[schemas.LeadItemResponse],
    summary="Discover & Score Leads via Research",
)
def discover_leads_endpoint(payload: schemas.LeadDiscoveryRequest) -> List[Dict[str, Any]]:
    """
    Discover genuine prospect entities via research.
    Calculates fit scores using multi-criteria algorithm; never fabricates personal emails.
    """
    discovered = lead_agent.discover_leads(
        vertical=payload.vertical,
        region=payload.region,
        search_terms=payload.search_terms,
    )
    # Save newly discovered genuine leads to database
    saved_leads = []
    for d in discovered:
        saved = models.insert_lead(
            name=d["name"],
            contact=d["contact"],
            vertical=d["vertical"],
            region=d["region"],
            fit_score=d["fit_score"],
            outreach_draft=d["outreach_draft"],
            source=d["source"],
            source_url=d["source_url"],
            scoring_breakdown=d["scoring_breakdown"],
        )
        saved_leads.append(saved)
    return saved_leads


@app.post(
    "/leads/{lead_id}/contact",
    response_model=schemas.LeadItemResponse,
    summary="Mark Lead as Contacted",
)
def mark_lead_contacted(lead_id: int) -> Dict[str, Any]:
    """Update lead status to 'contacted'."""
    models.update_lead_status(lead_id, "contacted")
    leads = models.list_leads()
    for l in leads:
        if l["id"] == lead_id:
            return l
    raise HTTPException(status_code=404, detail="Lead not found.")


# =====================================================================
# PDF Knowledge Pipeline & Library Endpoints
# =====================================================================

@app.post("/knowledge/ingest-pdfs", summary="Trigger PDF Ingestion into ChromaDB")
def ingest_pdfs_endpoint() -> Dict[str, Any]:
    """Extract and index all PDF documents in data/knowledge/pdfs/."""
    chunks = pdf_pipeline.ingest_all_pdfs()
    count = vector_store.index_pdf_chunks(chunks)
    stats = vector_store.get_company_knowledge_stats()
    return {
        "status": "success",
        "indexed_chunks": count,
        "library_stats": stats,
    }


@app.get("/knowledge/library", summary="Get Indexed PDF Knowledge Library Overview")
def get_knowledge_library() -> Dict[str, Any]:
    """Return overview of indexed PDF documents and chunks."""
    stats = vector_store.get_company_knowledge_stats()
    available_files = pdf_pipeline.list_available_pdfs()
    return {
        "stats": stats,
        "available_files": available_files,
    }


@app.post("/knowledge/retrieve", summary="Execute Hybrid Retrieval with Page Citations")
def retrieve_knowledge_endpoint(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Hybrid search returning ranked chunks with exact page numbers and document filenames."""
    query = payload.get("query", "")
    brand = payload.get("brand")
    product = payload.get("product")
    top_k = int(payload.get("top_k", 3))
    return knowledge_retriever.retrieve(brand=brand or "Jade", topic=query, product=product, top_k=top_k)


# =====================================================================
# Real Analytics: Risk Heatmap & Risk Metrics
# =====================================================================

@app.get("/analytics/risk-heatmap", summary="Dynamic Risk Heatmap (Database-Backed)")
def get_risk_heatmap_endpoint(group_by: str = Query("brand", regex="^(brand|platform)$")) -> Dict[str, Any]:
    """Return risk heatmap matrix calculated from actual database records."""
    return analytics_service.get_risk_heatmap(group_by=group_by)


@app.get("/analytics/top-issues", summary="Top Recurring Compliance Violations")
def get_top_issues_endpoint(limit: int = Query(5, ge=1, le=20)) -> List[Dict[str, Any]]:
    """Return most frequent compliance issues aggregated from reviewer feedback."""
    return analytics_service.get_top_recurring_issues(limit=limit)


@app.get("/analytics/risk-distribution", summary="Generated Assets Risk Level Distribution")
def get_risk_distribution_endpoint() -> Dict[str, int]:
    """Return count of generated content assets distributed by LOW, MEDIUM, HIGH risk."""
    return analytics_service.get_risk_distribution()


# =====================================================================
# Semantic Feedback Learning & Competitor Intelligence
# =====================================================================

@app.get("/feedback/semantic-search", summary="Search Historical Reviewer Feedback Semantically")
def semantic_feedback_search(
    query: str = Query(..., min_length=2),
    brand: Optional[str] = Query(None),
    top_k: int = Query(3, ge=1, le=10),
) -> List[Dict[str, Any]]:
    """Retrieve semantically similar historical corrections for generation context."""
    return feedback_agent.retrieve_semantic_feedback(
        topic=query,
        brand=brand or "Jade",
        top_k=top_k,
    )


@app.post("/competitors/research", summary="Analyze External Competitor Positioning")
def analyze_competitor_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract public competitor profile (messaging, claims, CTA, tone, positioning).
    Classified as Tier 3 External Intelligence.
    """
    comp = payload.get("competitor", "Generic Commercial Insurer")
    cat = payload.get("product_category", "Specialty Insurance")
    reg = payload.get("region", "Southeast Asia")
    return competitor_research_agent.analyze_competitor(
        competitor=comp,
        product_category=cat,
        region=reg,
    )
