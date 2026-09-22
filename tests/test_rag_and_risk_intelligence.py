"""
Test Suite for RAG + PDF Knowledge + Groq LLM + Semantic Feedback + Marketing Risk Engine.
Validates the new JA Assure AI Marketing Intelligence & Risk Agent capabilities.
"""

import pytest
from pathlib import Path
from backend.knowledge.pdf_pipeline import pdf_pipeline
from backend.knowledge.vector_store import vector_store
from backend.services.llm_service import MockTestProvider, LLMService, LLMGenerationError
from backend.services.analytics_service import get_risk_heatmap, get_top_recurring_issues, get_risk_distribution
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.content_agent import ContentAgent
from backend.agents.research_agent import CompetitorResearchAgent
from backend import models

TEST_DB = "data/test_rag_risk.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    p = Path(TEST_DB)
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_DB)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", TEST_DB)
    from backend.database import init_db
    init_db(TEST_DB)
    yield
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def test_pdf_pipeline_chunking_and_metadata():
    """Verify PDF pipeline extracts pages and tags chunks with required metadata."""
    chunks = pdf_pipeline.ingest_all_pdfs()
    assert len(chunks) > 0

    required_keys = {"chunk_id", "document_id", "filename", "page_number", "section", "product", "brand", "source", "document_type", "text"}
    for c in chunks:
        assert required_keys.issubset(c.keys())
        assert c["page_number"] >= 1
        assert len(c["text"]) > 20


def test_vector_store_hybrid_search():
    """Verify ChromaDB hybrid search ranks authoritative PDF chunks by brand and topic."""
    results = vector_store.hybrid_search("vault alarm and unattended vehicle transit", brand="Jade", top_k=2)
    assert len(results) > 0
    assert any("jewell" in r["filename"].lower() or r["brand"] == "Jade" for r in results)
    assert "page_number" in results[0]
    assert "relevance_score" in results[0]


def test_vector_store_semantic_feedback_indexing_and_search():
    """Verify reviewer corrections are embedded and retrieved semantically."""
    vector_store.index_feedback(
        feedback_id="fb_test_101",
        brand="Jade",
        tag="inaccurate_claim",
        note="Do not guarantee 100% loss recovery on high-value diamond transit. Always add terms qualifier.",
        flawed_content="We provide 100% guaranteed loss recovery on diamonds.",
        risk_score=75.0,
    )

    matches = vector_store.search_similar_feedback(
        query="Guaranteed complete loss recovery on precious stones",
        brand="Jade",
        top_k=1,
    )
    assert len(matches) > 0
    assert matches[0]["feedback_id"] == "fb_test_101"
    assert "tag" in matches[0]


def test_llm_service_provider_fallback():
    """Verify LLMService properly handles provider failover with Mock providers."""
    failing_provider = MockTestProvider("FailingProvider", "fail-model", should_fail=True)
    working_fallback = MockTestProvider("FallbackProvider", "fallback-model", should_fail=False)

    service = LLMService(primary_provider=failing_provider, fallback_provider=working_fallback)
    result = service.generate_content("Generate compliant post")

    assert result["provider"] == "FallbackProvider"
    assert result["model"] == "fallback-model"
    assert "content" in result


def test_llm_service_all_providers_fail_raises_clear_error():
    """Verify that if all providers fail, a clear LLMGenerationError is raised."""
    failing1 = MockTestProvider("P1", "m1", should_fail=True)
    failing2 = MockTestProvider("P2", "m2", should_fail=True)

    service = LLMService(primary_provider=failing1, fallback_provider=failing2)
    with pytest.raises(LLMGenerationError) as exc_info:
        service.generate_content("Generate compliant post")
    assert "failed across all available providers" in str(exc_info.value).lower() or "llm generation failed" in str(exc_info.value).lower()


def test_marketing_risk_engine_scoring_and_issues():
    """Verify ComplianceAgent outputs structured risk level, risk score, and issues array."""
    flawed_copy = "Get instant guaranteed payouts and 100% protection with zero risk today!"
    res = compliance_agent.check(flawed_copy, "Jade")

    assert res["status"] == "fail"
    assert res["status_display"] == "FAIL"
    assert res["risk_level"] in ("MEDIUM", "HIGH")
    assert res["risk_score"] > 30.0
    assert len(res["issues"]) > 0

    first_issue = res["issues"][0]
    assert "rule_id" in first_issue
    assert "issue_type" in first_issue
    assert "severity" in first_issue
    assert "evidence" in first_issue
    assert "explanation" in first_issue


def test_competitor_research_agent_extraction():
    """Verify CompetitorResearchAgent extracts 6-point structured competitive profile."""
    cra = CompetitorResearchAgent()
    profile = cra.analyze_competitor(
        competitor="Generic Marine Underwriter",
        industry="Insurance",
        region="Southeast Asia",
        product_category="Jewellers Block",
    )

    assert profile["competitor"] == "Generic Marine Underwriter"
    assert "messaging" in profile
    assert "claims" in profile and isinstance(profile["claims"], list)
    assert "cta" in profile
    assert "tone" in profile
    assert "themes" in profile and isinstance(profile["themes"], list)
    assert "positioning" in profile
    assert profile["tier"] == "TIER_3_EXTERNAL_INTELLIGENCE"


def test_database_driven_risk_heatmap_and_analytics():
    """Verify get_risk_heatmap and get_top_recurring_issues compute dynamically from SQLite."""
    # Insert items with issues
    item1 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Flawed copy 1",
        compliance_result={
            "status": "fail",
            "risk_level": "HIGH",
            "risk_score": 60.0,
            "issues": [
                {"rule_id": "NO_GUARANTEED_PAYOUT", "issue_type": "unsupported_guarantee", "severity": "HIGH"},
                {"rule_id": "NO_ABSOLUTE_PROTECTION", "issue_type": "inaccurate_claim", "severity": "HIGH"},
            ],
            "reasons": [{"rule": "NO_GUARANTEED_PAYOUT"}],
        },
        db_path=TEST_DB,
    )
    models.reject_content(item1["id"], tag="unsupported_guarantee", note="No payout guarantee", db_path=TEST_DB)

    heatmap = get_risk_heatmap(group_by="brand", db_path=TEST_DB)
    assert "columns" in heatmap
    assert "rows" in heatmap
    assert "Jade" in heatmap["columns"]
    row_types = [r["issue_type"] for r in heatmap["rows"]]
    assert "unsupported_guarantee" in row_types
    jade_row = next(r for r in heatmap["rows"] if r["issue_type"] == "unsupported_guarantee")
    assert jade_row["Jade"] >= 1

    top_issues = get_top_recurring_issues(limit=5, db_path=TEST_DB)
    assert len(top_issues) > 0
    assert any(i["issue_type"] == "unsupported_guarantee" for i in top_issues)

    dist = get_risk_distribution(db_path=TEST_DB)
    assert dist["HIGH"] >= 1
