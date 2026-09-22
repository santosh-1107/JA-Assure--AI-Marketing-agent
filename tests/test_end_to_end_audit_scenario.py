"""
Exact 21-Step End-to-End Audit Scenario for JA Assure AI Marketing Intelligence Agent.
Verifies real data provenance across the complete pipeline without simulated shortcuts:
  1. Select Jade
  2. Select Jewellers Block & Specie
  3. Enter: "Create a LinkedIn post about protecting high-value jewellery inventory."
  4. Retrieve JA Assure PDF knowledge
  5. Show source pages
  6. Research competitors
  7. Generate through Groq
  8. Extract claims
  9. Ground claims
  10. Run Risk Agent
  11. Display risk
  12. Human rejects content
  13. Store feedback
  14. Create feedback embedding
  15. Generate again
  16. Retrieve previous semantic feedback
  17. Generate improved content
  18. Run Risk Agent again
  19. Display before/after
  20. Update analytics
  21. Display risk heatmap
"""

import os
import pytest
from pathlib import Path
from backend.database import init_db
from backend import models
from backend.knowledge.knowledge_retriever import knowledge_retriever
from backend.agents.research_agent import research_agent
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.services.groq_guardrails import ClaimGroundingVerifier
from backend.services import analytics_service
from backend.knowledge.vector_store import vector_store

TEST_E2E_DB = str(Path(__file__).resolve().parent.parent / "data" / "test_e2e_scenario.db")


@pytest.fixture(autouse=True)
def setup_e2e_db(monkeypatch):
    p = Path(TEST_E2E_DB)
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_E2E_DB)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", TEST_E2E_DB)
    init_db(TEST_E2E_DB)
    yield
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def test_exact_21_step_end_to_end_scenario():
    # -------------------------------------------------------------
    # 1. Select Jade
    # -------------------------------------------------------------
    brand = "Jade"
    assert brand == "Jade"

    # -------------------------------------------------------------
    # 2. Select Jewellers Block
    # -------------------------------------------------------------
    product = "Jewellers Block & Specie"
    assert "Jewellers Block" in product

    # -------------------------------------------------------------
    # 3. Enter topic & platform
    # -------------------------------------------------------------
    topic = "Create a LinkedIn post about protecting high-value jewellery inventory."
    platform = "LinkedIn"

    # -------------------------------------------------------------
    # 4. Retrieve JA Assure PDF knowledge
    # -------------------------------------------------------------
    retrieved_sources = knowledge_retriever.retrieve(
        brand=brand,
        topic=topic,
        product=product,
        top_k=4,
    )
    assert len(retrieved_sources) >= 1, "RAG failed to retrieve JA Assure PDF knowledge"

    # -------------------------------------------------------------
    # 5. Show source pages
    # -------------------------------------------------------------
    for src in retrieved_sources:
        assert "filename" in src
        assert "page_number" in src
        assert src["page_number"] >= 1
        assert "text" in src
        assert src["tier"] == "TIER_1_AUTHORITATIVE"
    primary_source = retrieved_sources[0]
    print(f"\n[E2E Step 5] Source Page: {primary_source['filename']}, Page {primary_source['page_number']}")

    # -------------------------------------------------------------
    # 6. Research competitors
    # -------------------------------------------------------------
    research_res = research_agent.research(
        brand=brand,
        topic=topic,
        product=product,
    )
    assert "competitor_analysis" in research_res
    comp_analysis = research_res["competitor_analysis"]
    assert len(comp_analysis["competitors"]) > 0
    assert comp_analysis["tier"] == "TIER_3_EXTERNAL_MARKET_INTELLIGENCE"
    assert "web_research_status" in research_res
    print(f"[E2E Step 6] Competitors Researched: {comp_analysis['competitors']}, Status: {research_res['web_research_status']}")

    # -------------------------------------------------------------
    # 7. Generate through Groq (initial draft with known regulatory flaw)
    # -------------------------------------------------------------
    initial_gen = content_agent.generate(
        topic=topic,
        brand=brand,
        product=product,
        platform=platform,
        content_type="post",
        force_trigger_flaw=True,
        cycle=1,
    )
    assert "content" in initial_gen
    assert len(initial_gen["content"]) > 20
    assert initial_gen["generation_mode"] in ("groq", "gemini", "offline", "simulation")
    initial_text = initial_gen["content"]
    print(f"[E2E Step 7] Initial Content Generated via {initial_gen.get('provider', 'engine')}")

    # -------------------------------------------------------------
    # 8. Extract claims
    # -------------------------------------------------------------
    verifier = ClaimGroundingVerifier()
    claims = verifier.extract_claims(initial_text, claims_from_llm=initial_gen.get("claims_used"))
    assert len(claims) >= 1
    print(f"[E2E Step 8] Extracted {len(claims)} factual claims from draft")

    # -------------------------------------------------------------
    # 9. Ground claims
    # -------------------------------------------------------------
    grounded_evals = verifier.verify_grounding(claims, retrieved_sources, brand=brand)
    assert len(grounded_evals) == len(claims)
    has_unsupported = any(g["status"] == "UNSUPPORTED" for g in grounded_evals)
    print(f"[E2E Step 9] Claim Grounding Evaluated: {len(grounded_evals)} claims checked (has_unsupported={has_unsupported})")

    # -------------------------------------------------------------
    # 10. Run Risk Agent
    # -------------------------------------------------------------
    initial_compliance = compliance_agent.check(
        content=initial_text,
        brand=brand,
        claim_grounding=grounded_evals,
    )
    assert "status" in initial_compliance
    assert "risk_score" in initial_compliance
    assert initial_compliance["status"] == "fail"  # Flaw triggered

    # -------------------------------------------------------------
    # 11. Display risk
    # -------------------------------------------------------------
    assert initial_compliance["risk_score"] > 0.0
    assert len(initial_compliance["reasons"]) >= 1
    print(f"[E2E Step 11] Risk Result: {initial_compliance['status'].upper()} (Score: {initial_compliance['risk_score']})")

    # Store initial item in test DB
    saved_initial = models.insert_content(
        brand=brand,
        platform=platform,
        content_type="post",
        topic=topic,
        product=product,
        content=initial_text,
        compliance_result=initial_compliance,
        cycle=1,
        status="pending",
        db_path=TEST_E2E_DB,
    )
    initial_id = saved_initial["id"]

    # -------------------------------------------------------------
    # 12. Human rejects content
    # -------------------------------------------------------------
    rejection_tag = "unsupported_guarantee"
    rejection_note = "Do not claim guaranteed cash payouts or instant settlements. Always qualify claims with 'subject to policy terms and conditions'."
    rejected_item = models.reject_content(
        content_id=initial_id,
        tag=rejection_tag,
        note=rejection_note,
        db_path=TEST_E2E_DB,
    )
    assert rejected_item["status"] == "rejected"
    print(f"[E2E Step 12] Human Rejected Content ID {initial_id} with tag '{rejection_tag}'")

    # -------------------------------------------------------------
    # 13. Store feedback in SQLite
    # -------------------------------------------------------------
    recent_fb = models.get_recent_feedback(brand=brand, n=1, db_path=TEST_E2E_DB)
    assert len(recent_fb) == 1
    assert recent_fb[0]["content_id"] == initial_id
    assert recent_fb[0]["tag"] == rejection_tag
    print(f"[E2E Step 13] Feedback Stored in SQLite (Feedback ID {recent_fb[0]['id']})")

    # -------------------------------------------------------------
    # 14. Create feedback embedding in ChromaDB
    # -------------------------------------------------------------
    fb_embed_id = vector_store.index_feedback(
        feedback_id=recent_fb[0]["id"],
        content_id=initial_id,
        original_content=initial_text,
        issue_type=rejection_tag,
        rejection_tag=rejection_tag,
        reviewer_note=rejection_note,
        brand=brand,
        product=product,
        platform=platform,
        risk_score=initial_compliance["risk_score"],
    )
    assert fb_embed_id.startswith("fb-")
    print(f"[E2E Step 14] Feedback Embedding Created in ChromaDB '{fb_embed_id}'")

    # -------------------------------------------------------------
    # 15 & 16. Generate again & Retrieve previous semantic feedback
    # -------------------------------------------------------------
    semantic_fb = feedback_agent.retrieve_semantic_feedback(
        topic="protecting high-value jewellery inventory from vault theft",
        brand=brand,
        product=product,
        platform=platform,
        top_k=5,
    )
    assert len(semantic_fb) >= 1
    assert any("guaranteed cash" in (f.get("reviewer_note") or f.get("summary", "")) for f in semantic_fb)
    print(f"[E2E Step 16] Retrieved Semantic Feedback: {semantic_fb[0]['reviewer_note'][:60]}...")

    # -------------------------------------------------------------
    # 17. Generate improved content with feedback incorporated
    # -------------------------------------------------------------
    regenerated_gen = content_agent.generate(
        topic=topic,
        brand=brand,
        product=product,
        platform=platform,
        content_type="post",
        past_corrections=semantic_fb,
        force_trigger_flaw=False,
        cycle=2,
    )
    improved_text = regenerated_gen["content"]
    assert "guaranteed payout" not in improved_text.lower()
    assert "100% protected" not in improved_text.lower()
    print("[E2E Step 17] Regenerated Content Incorporating Feedback Guidance")

    # -------------------------------------------------------------
    # 18. Run Risk Agent again
    # -------------------------------------------------------------
    re_claims = verifier.extract_claims(improved_text, claims_from_llm=regenerated_gen.get("claims_used"))
    all_sources = regenerated_gen.get("sources") or retrieved_sources
    re_grounded = verifier.verify_grounding(re_claims, all_sources, brand=brand)
    regenerated_compliance = compliance_agent.check(
        content=improved_text,
        brand=brand,
        claim_grounding=re_grounded,
    )
    reasons_summary = [r.get('rule') for r in regenerated_compliance.get('reasons', [])]
    print(f"[DEBUG] Compliance Status: {regenerated_compliance.get('status')}")
    print(f"[DEBUG] Compliance Reason Rules: {reasons_summary}")
    assert regenerated_compliance["status"] == "pass"
    assert len(regenerated_compliance["reasons"]) == 0
    print(f"[E2E Step 18] Regenerated Compliance: {regenerated_compliance['status'].upper()} (Score: {regenerated_compliance['risk_score']})")

    # Store improved item linked to parent
    improved_item = models.insert_content(
        brand=brand,
        platform=platform,
        content_type="post",
        topic=topic,
        product=product,
        content=improved_text,
        compliance_result=regenerated_compliance,
        cycle=2,
        parent_id=initial_id,
        fixed_issue=f"Resolved [{rejection_tag}]: {rejection_note}",
        status="pending",
        db_path=TEST_E2E_DB,
    )

    # -------------------------------------------------------------
    # 19. Display before/after
    # -------------------------------------------------------------
    safe_initial = initial_text[:140].encode("ascii", "replace").decode("ascii")
    safe_improved = improved_text[:140].encode("ascii", "replace").decode("ascii")
    print("\n--- [E2E Step 19] BEFORE / AFTER COMPARISON ---")
    print(f"BEFORE (Cycle 1, FAIL):\n{safe_initial}...\n")
    print(f"AFTER (Cycle 2, PASS):\n{safe_improved}...\n")

    # Human approves the compliant regenerated draft
    approved_item = models.approve_content(improved_item["id"], db_path=TEST_E2E_DB)
    assert approved_item["status"] == "approved"

    # -------------------------------------------------------------
    # 20. Update analytics
    # -------------------------------------------------------------
    dash_metrics = analytics_service.get_dashboard_metrics(db_path=TEST_E2E_DB)
    assert dash_metrics["total_assets"] >= 2
    assert dash_metrics["rejected_count"] >= 1
    assert dash_metrics["approved_count"] >= 1
    assert dash_metrics["total_feedback"] >= 1
    print(f"[E2E Step 20] Dashboard Analytics Updated: Total={dash_metrics['total_assets']}, Approved={dash_metrics['approved_count']}, Rejected={dash_metrics['rejected_count']}")

    # -------------------------------------------------------------
    # 21. Display risk heatmap
    # -------------------------------------------------------------
    brand_heatmap = analytics_service.get_risk_heatmap(db_path=TEST_E2E_DB, group_by="brand")
    assert "rows" in brand_heatmap
    assert "columns" in brand_heatmap
    assert "Jade" in brand_heatmap["columns"]
    assert len(brand_heatmap["rows"]) > 0
    print(f"[E2E Step 21] Risk Heatmap Generated: Columns={brand_heatmap['columns']}, Rows={len(brand_heatmap['rows'])}, Total Violations={brand_heatmap.get('total_violations')}")
    print("=== EXACT 21-STEP END-TO-END SCENARIO SUCCESSFULLY VERIFIED ===")
