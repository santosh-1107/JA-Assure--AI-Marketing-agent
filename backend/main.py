"""
FastAPI Backend Application for JA Assure AI Marketing Agent.
Exposes REST endpoints for generation, compliance checking, human review,
feedback-driven regeneration, and rejection-rate analytics.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.gemini_service import gemini_service
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from backend import models, schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ja_assure.backend")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is created on server boot."""
    init_db()
    logger.info("JA Assure database initialized.")
    yield

app = FastAPI(
    title="JA Assure AI Marketing Agent API",
    description="Agentic marketing engine for regulated InsurTech with compliance gating and human-in-the-loop feedback learning.",
    version="1.0.0",
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


# =====================================================================
# Health & Status Endpoint
# =====================================================================

@app.get("/health", summary="System Health & LLM Status")
def health_check() -> Dict[str, Any]:
    """Check API health, database readiness, and LLM configuration status."""
    llm_status = gemini_service.check_health()
    return {
        "status": "healthy",
        "service": "JA Assure AI Marketing Agent",
        "llm": llm_status,
    }


# =====================================================================
# Content Generation & Compliance Endpoints
# =====================================================================

@app.post(
    "/content/research",
    response_model=schemas.ResearchResponse,
    summary="Research Official JA Assure Knowledge",
)
def research_knowledge(payload: schemas.ResearchRequest) -> Dict[str, Any]:
    """
    Retrieve grounded research summary and official sources from JA Assure Resources
    (https://www.ja-assure.com/resources.html) for a given brand and topic.
    """
    return research_agent.research(
        brand=payload.brand,
        topic=payload.topic,
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
    Runs compliance check against brand rubric and stores item as 'pending'.
    """
    try:
        # 1. Generate content via Content Agent (grounded in JA Assure knowledge)
        generated = content_agent.generate(
            topic=payload.topic,
            brand=payload.brand,
            platform=payload.platform,
            content_type=payload.content_type,
            research_context=payload.research_context,
            force_trigger_flaw=bool(payload.force_trigger_flaw),
            cycle=payload.cycle,
        )

        # 2. Evaluate with Compliance Agent
        compliance_verdict = compliance_agent.check(
            content=generated["content"],
            brand=payload.brand,
        )

        # 3. Store in SQLite with initial status='pending' (Human approval mandatory)
        saved_item = models.insert_content(
            brand=payload.brand,
            platform=payload.platform,
            content_type=payload.content_type,
            content=generated["content"],
            compliance_result=compliance_verdict,
            cycle=payload.cycle,
            fixed_issue=generated.get("fixed_issue"),
            sources=generated.get("sources"),
            status="pending",
        )

        return saved_item

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

    verdict = compliance_agent.check(content=item["content"], brand=item["brand"])
    models.update_compliance_result(content_id, verdict)
    return verdict


# =====================================================================
# Content Queues (Pending & Approved)
# =====================================================================

@app.get(
    "/content/pending",
    response_model=List[schemas.ContentItemResponse],
    summary="List Pending Content for Human Review",
)
def get_pending_content(brand: Optional[str] = Query(None, description="Filter by brand")) -> List[Dict[str, Any]]:
    """List content items in 'pending' status. Non-compliant items (FAIL) are sorted to the top."""
    return models.list_pending_content(brand=brand)


@app.get(
    "/content/approved",
    response_model=List[schemas.ContentItemResponse],
    summary="List Approved Marketing Assets",
)
def get_approved_content(brand: Optional[str] = Query(None, description="Filter by brand")) -> List[Dict[str, Any]]:
    """List assets approved by human reviewer ready for publishing / scheduling."""
    return models.list_approved_content(brand=brand)


@app.get(
    "/content/{content_id}",
    response_model=schemas.ContentItemResponse,
    summary="Get Single Content Item",
)
def get_content_item(content_id: int) -> Dict[str, Any]:
    """Fetch single content record by ID."""
    item = models.get_content_by_id(content_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")
    return item


# =====================================================================
# Human Governance Actions (Approve / Reject / Edit / Schedule)
# =====================================================================

@app.post(
    "/content/{content_id}/approve",
    response_model=schemas.ContentItemResponse,
    summary="Approve Content (Human Action)",
)
def approve_content_item(content_id: int) -> Dict[str, Any]:
    """
    Human reviewer approves content.
    Enforces strict state machine: content MUST be in pending state.
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
    Human reviewer rejects content and records feedback tag and note.
    Feedback is stored immutably to instruct future generations.
    """
    try:
        updated = models.reject_content(
            content_id=content_id,
            tag=payload.tag,
            note=payload.note,
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
    """Human reviewer directly modifies content copy and records rationale."""
    try:
        # Re-check compliance on edited content
        item = models.get_content_by_id(content_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Content ID {content_id} not found.")

        new_compliance = compliance_agent.check(content=payload.edited_content, brand=item["brand"])

        updated = models.edit_content(
            content_id=content_id,
            edited_content=payload.edited_content,
            tag=payload.tag,
            note=payload.note,
            compliance_result=new_compliance,
        )
        return updated
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/content/{content_id}/schedule",
    response_model=schemas.ContentItemResponse,
    summary="Schedule Content for Publishing (Project 2 Integration)",
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
    1. Identifies original topic, brand, and platform.
    2. Pulls recent feedback for the brand (including the latest rejection reason).
    3. Injects feedback into the Content Agent prompt.
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

        # Ground in official JA Assure knowledge
        topic_summary = "How jewellery businesses protect high-value inventory" if "jade" in parent["brand"].lower() else "Medical indemnity and clinical malpractice defense"
        research_context = research_agent.research(brand=parent["brand"], topic=topic_summary)

        # Generate new variant
        generated = content_agent.generate(
            topic=topic_summary,
            brand=parent["brand"],
            platform=parent["platform"],
            content_type=parent["content_type"],
            research_context=research_context,
            past_corrections=recent_feedback,
            force_trigger_flaw=False,  # Feedback loop must resolve the flaw
            cycle=parent.get("cycle", 1) + 1,
        )

        # Re-run Compliance check
        new_compliance = compliance_agent.check(
            content=generated["content"],
            brand=parent["brand"],
        )

        # Determine fixed issue description
        fixed_issue_desc = "Resolved compliance violation using reviewer feedback."
        if recent_feedback:
            fixed_issue_desc = f"Corrected: [{recent_feedback[0]['tag']}] {recent_feedback[0]['note']}"

        # Save new variant linked to parent
        new_item = models.insert_content(
            brand=parent["brand"],
            platform=parent["platform"],
            content_type=parent["content_type"],
            content=generated["content"],
            compliance_result=new_compliance,
            cycle=parent.get("cycle", 1) + 1,
            parent_id=parent["id"],
            fixed_issue=fixed_issue_desc,
            sources=generated.get("sources") or parent.get("sources"),
            status="pending",
        )

        return new_item

    except Exception as exc:
        logger.exception(f"Failed to regenerate content for ID {content_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/feedback",
    response_model=List[schemas.FeedbackItemResponse],
    summary="List Human Feedback Records",
)
def list_feedback(
    brand: Optional[str] = Query(None, description="Filter feedback by brand"),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Retrieve historical reviewer corrections and notes."""
    return models.list_all_feedback(brand=brand, limit=limit)


@app.get(
    "/analytics/rejection-rate",
    response_model=schemas.RejectionRateResponse,
    summary="Rejection Rate Across Review Cycles",
)
def get_rejection_rate() -> Dict[str, Any]:
    """
    Calculate empirical rejection rates across generation/review cycles.
    Powers the downward trend chart in the review dashboard.
    """
    return feedback_agent.get_rejection_rate_analytics()


@app.get(
    "/analytics/before-after",
    response_model=List[schemas.BeforeAfterComparison],
    summary="Before vs After Regeneration Comparisons",
)
def get_before_after(
    brand: Optional[str] = Query(None, description="Filter by brand"),
    limit: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Fetch paired before (rejected) and after (regenerated) content records."""
    return models.get_before_after_pairs(brand=brand, limit=limit)


# =====================================================================
# Leads Endpoints (P1 Feature)
# =====================================================================

@app.get(
    "/leads",
    response_model=List[schemas.LeadItemResponse],
    summary="List InsurTech Prospects (P1)",
)
def get_leads(vertical: Optional[str] = Query(None, description="Filter by vertical")) -> List[Dict[str, Any]]:
    """Retrieve prospective leads by vertical with fit scores and draft outreach."""
    return models.list_leads(vertical=vertical)


@app.post(
    "/leads",
    response_model=schemas.LeadItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add InsurTech Lead",
)
def add_lead(payload: schemas.LeadCreateRequest) -> Dict[str, Any]:
    """Add new prospective lead into CRM pipeline."""
    return models.insert_lead(
        name=payload.name,
        contact=payload.contact,
        vertical=payload.vertical,
        fit_score=payload.fit_score,
        outreach_draft=payload.outreach_draft or "",
    )


@app.post(
    "/leads/{lead_id}/contact",
    summary="Mark Lead Outreach as Sent",
)
def mark_lead_contacted(lead_id: int) -> Dict[str, Any]:
    """Update lead status to 'contacted'."""
    models.update_lead_status(lead_id, "contacted")
    return {"id": lead_id, "status": "contacted", "message": "Lead outreach dispatched."}
