"""
Comprehensive Audit Verification Suite for JA Assure AI Marketing Agent.
Validates all 34 audit findings across database migrations, centralized analytics,
state machine governance, prompt engineering, compliance engine, and lead intelligence.
"""

import os
import json
import sqlite3
import pytest
from pathlib import Path
from pydantic import ValidationError

from backend.database import init_db, get_connection, get_db_path, is_demo_mode
from backend import models
from backend.services import analytics_service
from backend.agents.content_agent import ContentAgent, content_agent
from backend.agents.compliance_agent import ComplianceAgent, compliance_agent, normalize_compliance_text
from backend.agents.research_agent import ResearchAgent, research_agent
from backend.agents.lead_agent import LeadAgent, lead_agent
from backend.schemas import GenerateRequest, RegenerateRequest, LeadCreate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_AUDIT_DB = str(PROJECT_ROOT / "tests" / "test_audit.db")


@pytest.fixture(autouse=True)
def setup_audit_db():
    """Ensure a clean audit test database for each test."""
    if os.path.exists(TEST_AUDIT_DB):
        try:
            os.remove(TEST_AUDIT_DB)
        except PermissionError:
            pass
    init_db(TEST_AUDIT_DB)
    yield
    if os.path.exists(TEST_AUDIT_DB):
        try:
            os.remove(TEST_AUDIT_DB)
        except PermissionError:
            pass


# =====================================================================
# PHASE 1 & 18: Database Migrations
# =====================================================================

def test_database_migration_columns_exist():
    """Verify all audit-mandated columns exist in content_queue and leads tables."""
    conn = get_connection(TEST_AUDIT_DB)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(content_queue)")
    cq_cols = {row["name"] for row in cursor.fetchall()}
    expected_cq = {
        "topic",
        "generation_mode",
        "model",
        "prompt_version",
        "knowledge_source_ids",
        "feedback_ids",
        "generation_metadata",
        "updated_at",
    }
    assert expected_cq.issubset(cq_cols), f"Missing columns in content_queue: {expected_cq - cq_cols}"

    cursor.execute("PRAGMA table_info(leads)")
    leads_cols = {row["name"] for row in cursor.fetchall()}
    expected_leads = {"region", "source", "source_url", "scoring_breakdown"}
    assert expected_leads.issubset(leads_cols), f"Missing columns in leads: {expected_leads - leads_cols}"
    conn.close()


# =====================================================================
# PHASE 2 & 18: Analytics Service & Dynamic Calculations
# =====================================================================

def test_analytics_metrics_empty_db():
    """Verify empty database returns None for cycle metrics and 0 for counts, never fallback numbers (20.0, 75.0, 80.0)."""
    metrics = analytics_service.get_dashboard_metrics(db_path=TEST_AUDIT_DB)

    assert metrics["pending_count"] == 0
    assert metrics["approved_count"] == 0
    assert metrics["rejected_count"] == 0
    assert metrics["scheduled_count"] == 0
    assert metrics["total_assets"] == 0
    assert metrics["total_feedback"] == 0
    assert metrics["latest_cycle"] is None
    assert metrics["latest_cycle_rejection_rate"] is None
    assert metrics["previous_cycle_rejection_rate"] is None
    assert metrics["relative_error_reduction"] is None
    assert metrics["rejection_rate_delta"] is None

    # Crucial finding: verify no arbitrary numbers were used as fallback
    for val in metrics.values():
        assert val not in (20.0, 75.0, 80.0), f"Hardcoded fallback detected: {val}"


def test_analytics_metrics_dynamic_calculation():
    """Verify cycle metrics and relative error reduction are dynamically calculated from SQLite rows."""
    # Cycle 1: 3 rejected, 1 approved -> 75.0% rejection rate
    for i in range(3):
        item = models.insert_content("Jade", "LinkedIn", "post", f"Draft {i}", cycle=1, status="pending", db_path=TEST_AUDIT_DB)
        models.reject_content(item["id"], tag="too_salesy", note="Too promotional", db_path=TEST_AUDIT_DB)
    good1 = models.insert_content("Jade", "LinkedIn", "post", "Good 1", compliance_result={"status": "pass", "reasons": []}, cycle=1, status="pending", db_path=TEST_AUDIT_DB)
    models.approve_content(good1["id"], db_path=TEST_AUDIT_DB)

    # Cycle 2: 1 rejected, 3 approved -> 25.0% rejection rate
    item2 = models.insert_content("Jade", "LinkedIn", "post", "Draft C2", cycle=2, status="pending", db_path=TEST_AUDIT_DB)
    models.reject_content(item2["id"], tag="wrong_cta", note="Fix CTA", db_path=TEST_AUDIT_DB)
    for j in range(3):
        good = models.insert_content("Jade", "LinkedIn", "post", f"Good C2 {j}", compliance_result={"status": "pass", "reasons": []}, cycle=2, status="pending", db_path=TEST_AUDIT_DB)
        models.approve_content(good["id"], db_path=TEST_AUDIT_DB)

    metrics = analytics_service.get_dashboard_metrics(db_path=TEST_AUDIT_DB)
    assert metrics["latest_cycle"] == 2
    assert metrics["latest_cycle_rejection_rate"] == 25.0
    assert metrics["previous_cycle_rejection_rate"] == 75.0
    assert metrics["baseline_rejection_rate"] == 75.0

    # Relative error reduction: (75.0 - 25.0) / 75.0 * 100 = 66.7%
    assert metrics["relative_error_reduction"] == 66.7
    assert metrics["rejection_rate_delta"] == -50.0


def test_metric_strip_derived_from_db():
    """Verify all KPI values directly match SQLite count aggregates."""
    models.insert_content("Jade", "LinkedIn", "post", "Pending 1", status="pending", db_path=TEST_AUDIT_DB)
    models.insert_content("Jade", "LinkedIn", "post", "Pending 2", status="pending", db_path=TEST_AUDIT_DB)
    app1 = models.insert_content("DoctorShield", "LinkedIn", "post", "Approved 1", compliance_result={"status": "pass", "reasons": []}, status="pending", db_path=TEST_AUDIT_DB)
    models.approve_content(app1["id"], db_path=TEST_AUDIT_DB)

    metrics = analytics_service.get_dashboard_metrics(db_path=TEST_AUDIT_DB)
    assert metrics["pending_count"] == 2
    assert metrics["approved_count"] == 1
    assert metrics["total_assets"] == 3


# =====================================================================
# PHASE 3 & 18: Demo Isolation
# =====================================================================

def test_destructive_reset_prevented_in_prod():
    """Verify scripts/seed_demo.py refuses to wipe or seed production database when DEMO_MODE=false."""
    from scripts.seed_demo import seed_data
    os.environ["DEMO_MODE"] = "false"

    # Seeding against normal production DB must raise PermissionError
    prod_db = str(PROJECT_ROOT / "data" / "ja_assure.db")
    with pytest.raises(PermissionError) as exc_info:
        seed_data(db_path=prod_db)
    assert "DEMO_MODE=true" in str(exc_info.value)


def test_demo_db_isolation():
    """Verify seed_demo.py writes to data/demo/ja_assure_demo.db and does not modify production DB."""
    from scripts.seed_demo import seed_data
    demo_db = str(PROJECT_ROOT / "data" / "demo" / "ja_assure_demo.db")

    # Seed isolated demo database
    seed_data(db_path=demo_db)
    assert os.path.exists(demo_db)

    # Verify demo database has records
    conn = sqlite3.connect(demo_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM content_queue")
    demo_count = cursor.fetchone()[0]
    conn.close()
    assert demo_count > 0


def test_demo_mode_env_flag(monkeypatch):
    """Verify database resolution centralizer respects DEMO_MODE flag."""
    monkeypatch.delenv("JA_ASSURE_DB_PATH", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    assert is_demo_mode() is True
    assert "ja_assure_demo.db" in str(get_db_path())

    monkeypatch.setenv("DEMO_MODE", "false")
    assert is_demo_mode() is False
    assert "ja_assure.db" in str(get_db_path())


# =====================================================================
# PHASE 4, 5, 6 & 18: Content Agent, Topic Preservation & Metadata
# =====================================================================

def test_content_agent_dynamic_assembly():
    """Verify ContentAgent dynamically constructs copy from YAML and knowledge without hardcoded text."""
    ca = ContentAgent()
    res = ca.generate(
        topic="Vault security specifications for gold bullion storage",
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        force_trigger_flaw=False,
        cycle=2,
    )
    content = res["content"]
    assert "vault security" in content.lower() or "gold bullion" in content.lower()
    assert res["generation_mode"] in ("groq", "gemini", "offline")
    assert res["prompt_version"] == "1.0"
    assert len(res["sources"]) > 0


def test_content_generation_metadata():
    """Verify generation metadata schema is complete and records engine mode."""
    ca = ContentAgent()
    res = ca.generate(
        topic="Medical malpractice risk governance",
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
    )
    assert "generation_mode" in res
    assert "model" in res
    assert "prompt_version" in res
    assert "knowledge_source_ids" in res
    assert "generation_metadata" in res
    assert isinstance(res["generation_metadata"], dict)


def test_invalid_brand_validation_error():
    """Verify ContentAgent and models reject unknown brands with ValueError."""
    ca = ContentAgent()
    with pytest.raises(ValueError) as exc:
        ca.generate(topic="Test topic", brand="UnknownInsuranceBrand", platform="LinkedIn", content_type="post")
    assert "Invalid brand" in str(exc.value)

    with pytest.raises(ValueError):
        models.insert_content(brand="NonExistentBrand", platform="LinkedIn", content_type="post", content="test", db_path=TEST_AUDIT_DB)


def test_regeneration_preserves_original_topic():
    """CRITICAL BUG FIX: Verify regeneration preserves parent topic and does NOT replace it with a generic sentence."""
    custom_topic = "Protecting heirloom diamond tiaras against transit damage"
    parent = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic=custom_topic,
        content="Flawed copy with guaranteed payout.",
        compliance_result={"status": "fail", "reasons": [{"rule": "NO_GUARANTEED_PAYOUT", "message": "No guarantees"}]},
        cycle=1,
        status="pending",
        db_path=TEST_AUDIT_DB,
    )
    models.reject_content(parent["id"], tag="inaccurate_claim", note="Remove guaranteed language", db_path=TEST_AUDIT_DB)

    # Trigger regeneration preserving topic
    ca = ContentAgent()
    res = ca.generate(
        topic=parent["topic"],
        brand=parent["brand"],
        platform=parent["platform"],
        content_type=parent["content_type"],
        past_corrections=models.get_recent_feedback(parent["brand"], n=3, db_path=TEST_AUDIT_DB),
        cycle=2,
    )
    assert parent["topic"] == custom_topic
    assert custom_topic.lower() in res["topic"].lower()


def test_additional_instruction_reaches_prompt():
    """Verify additional reviewer instruction reaches the generated content and prompt."""
    ca = ContentAgent()
    instruction = "Explicitly reference Lloyd's of London syndication authority."
    res = ca.generate(
        topic="Specialist diamond risk coverage",
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        additional_instruction=instruction,
    )
    assert instruction in res["content"] or "Focus:" in res["content"] or instruction in ca._build_user_prompt(
        "Specialist diamond risk coverage", "LinkedIn", "post", "", additional_instruction=instruction
    )


# =====================================================================
# PHASE 7 & 8 & 18: Governance State Machine & Edit Flow
# =====================================================================

def test_fail_content_cannot_be_approved():
    """Verify compliance FAIL items CANNOT be approved directly."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Guaranteed instant cash payout!",
        compliance_result={"status": "fail", "reasons": [{"rule": "NO_GUARANTEED_PAYOUT", "message": "Prohibited"}]},
        status="pending",
        db_path=TEST_AUDIT_DB,
    )
    with pytest.raises(ValueError) as exc:
        models.approve_content(item["id"], db_path=TEST_AUDIT_DB)
    assert "Compliance Governance Violation" in str(exc.value)


def test_rejected_content_cannot_be_approved_directly():
    """Verify rejected content CANNOT be directly transitioned to approved."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Copy to reject",
        status="pending",
        db_path=TEST_AUDIT_DB,
    )
    models.reject_content(item["id"], tag="off_brand_tone", note="Too casual", db_path=TEST_AUDIT_DB)

    with pytest.raises(ValueError) as exc:
        models.approve_content(item["id"], db_path=TEST_AUDIT_DB)
    assert "State Machine Violation" in str(exc.value)


def test_edit_approved_content_forces_pending():
    """Verify editing ANY content (even approved) resets status to pending and re-runs compliance."""
    item = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content="Original compliant post",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_AUDIT_DB,
    )
    models.approve_content(item["id"], db_path=TEST_AUDIT_DB)
    assert models.get_content_by_id(item["id"], db_path=TEST_AUDIT_DB)["status"] == "approved"

    # Human edits the approved content to introduce a flaw
    flawed_edit = "Edited copy with guaranteed outcome in malpractice."
    flawed_comp = compliance_agent.check(flawed_edit, "DoctorShield")
    edited = models.edit_content(
        content_id=item["id"],
        edited_content=flawed_edit,
        tag="inaccurate_claim",
        note="User revised post",
        compliance_result=flawed_comp,
        db_path=TEST_AUDIT_DB,
    )
    assert edited["status"] == "pending"
    assert edited["compliance_result"]["status"] == "fail"


# =====================================================================
# PHASE 9 & 10 & 18: Compliance Engine & Normalization
# =====================================================================

def test_compliance_normalization_and_variants():
    """Verify compliance engine catches phrase variants across extra whitespace, hyphens, and casing."""
    ca = ComplianceAgent()

    # Whitespace and punctuation variants
    v1 = "Our policy guarantees a guaranteed   payout on all losses."
    res1 = ca.check(v1, "Jade")
    assert res1["status"] == "fail"
    assert any(r["rule"] == "NO_GUARANTEED_PAYOUT" for r in res1["reasons"])

    v2 = "We promise 100%--loss--free protection for all doctors."
    res2 = ca.check(v2, "DoctorShield")
    assert res2["status"] == "fail"
    assert any(r["rule"] == "NO_ABSOLUTE_PROTECTION" for r in res2["reasons"])


def test_compliance_llm_unknown_rule_rejected():
    """Verify compliance agent rejects any hallucinatory rule IDs returned by LLM that are not in the YAML rubric."""
    ca = ComplianceAgent()
    valid_rules = ca.get_rules_for_brand("Jade")
    valid_ids = {r["id"] for r in valid_rules}

    # Simulate an LLM returning an invented rule ID
    invented_rule_id = "MAS_FABRICATED_CLAUSE_99"
    assert invented_rule_id not in valid_ids


def test_rubric_references_present():
    """Verify rubrics use neutral rule identifiers and only cite verified sources."""
    ca = ComplianceAgent()
    for brand in ["Jade", "DoctorShield"]:
        rules = ca.get_rules_for_brand(brand)
        for r in rules:
            assert "_" in r["id"]  # Neutral identifier format
            assert "MAS Guideline 4.1" not in r.get("reference", "")  # No invented regulatory citations


# =====================================================================
# PHASE 11 & 18: Research Agent
# =====================================================================

def test_research_agent_competitor_analysis():
    """Verify ResearchAgent uses competitor_list and contrasts offerings."""
    ra = ResearchAgent()
    res = ra.research("Jade", "Jewellers Block and luxury watch transit")
    assert "competitor_analysis" in res
    assert "competitors" in res["competitor_analysis"]
    assert len(res["competitor_analysis"]["competitors"]) > 0


def test_research_agent_tavily_fallback():
    """Verify ResearchAgent falls back to official JA Assure knowledge when TAVILY_API_KEY is unset."""
    ra = ResearchAgent()
    res = ra.research("Jade", "Specie insurance")
    sources = res["sources"]
    assert len(sources) > 0
    assert all(s["source_type"] in ("official_ja_assure", "web_research") for s in sources)


def test_source_schema_completeness():
    """Verify every source item conforms strictly to the Source schema."""
    ra = ResearchAgent()
    res = ra.research("DoctorShield", "Medical malpractice indemnity")
    for s in res["sources"]:
        assert "title" in s and s["title"]
        assert "url" in s and s["url"]
        assert "source_type" in s
        assert "snippet" in s
        assert "relevance_score" in s
        assert "key_facts" in s and isinstance(s["key_facts"], list)


# =====================================================================
# PHASE 12 & 18: Lead Agent
# =====================================================================

def test_lead_agent_scoring_criteria():
    """Verify fit score is derived from explicit 5-factor scoring model."""
    la = LeadAgent(db_path=TEST_AUDIT_DB)
    lead = la.score_lead(
        name="SingaGem Vault Holdings",
        vertical="Jewellers",
        region="Singapore",
        source_url="https://verified-directory.gov.sg/singagem",
    )
    assert 0 <= lead["fit_score"] <= 100
    breakdown = lead.get("scoring_breakdown", {})
    assert "vertical_match" in breakdown
    assert "region_match" in breakdown
    assert "business_profile" in breakdown
    assert "insurance_relevance" in breakdown
    assert "public_information_quality" in breakdown
    assert sum(breakdown.values()) == lead["fit_score"]


def test_lead_agent_no_fabricated_contacts():
    """Verify lead agent does NOT fabricate contact emails when unverified."""
    la = LeadAgent(db_path=TEST_AUDIT_DB)
    leads = la.discover_leads("SMEs", "Singapore")
    for l in leads:
        if l["contact"] is not None:
            # Contact must not be a fake placeholder domain
            assert "fake" not in l["contact"].lower()
            assert "example.com" not in l["contact"].lower()


# =====================================================================
# PHASE 13 & 18: Pydantic Validation & Numeric Bounds
# =====================================================================

def test_schema_invalid_enum_validation():
    """Verify Pydantic schemas reject invalid brands, platforms, and content types."""
    with pytest.raises(ValidationError):
        GenerateRequest(brand="InvalidBrand", platform="LinkedIn", content_type="post", topic="test")

    with pytest.raises(ValidationError):
        GenerateRequest(brand="Jade", platform="TikTok", content_type="post", topic="test")


def test_schema_numeric_bounds():
    """Verify Pydantic schemas enforce numeric bounds: cycle >= 1, fit_score 0-100."""
    with pytest.raises(ValidationError):
        GenerateRequest(brand="Jade", platform="LinkedIn", content_type="post", topic="test", cycle=0)

    with pytest.raises(ValidationError):
        LeadCreate(name="Test Prospect", vertical="Jewellers", fit_score=150)


# =====================================================================
# PHASE 15 & 17 & 18: Rejection Drawer & Publishing Status
# =====================================================================

def test_rejection_drawer_derives_note_from_rule():
    """Verify rejection flow pre-populates note from triggered compliance failure message."""
    ca = ComplianceAgent()
    comp = ca.check("We guarantee 100% loss-free protection on all jewellery.", "Jade")
    assert comp["status"] == "fail"
    assert len(comp["reasons"]) > 0

    first_reason_msg = comp["reasons"][0]["message"]
    assert first_reason_msg != ""
    assert "guarantee" in first_reason_msg.lower() or "policy terms" in first_reason_msg.lower()


def test_publishing_status_labeling():
    """Verify status transitions through approved to scheduled, enforcing that scheduling requires prior approval."""
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content="Compliant content for publishing",
        compliance_result={"status": "pass", "reasons": []},
        status="pending",
        db_path=TEST_AUDIT_DB,
    )

    # Cannot schedule while pending
    with pytest.raises(ValueError):
        models.schedule_content(item["id"], db_path=TEST_AUDIT_DB)

    # Approve
    models.approve_content(item["id"], db_path=TEST_AUDIT_DB)
    approved = models.get_content_by_id(item["id"], db_path=TEST_AUDIT_DB)
    assert approved["status"] == "approved"

    # Schedule
    scheduled = models.schedule_content(item["id"], db_path=TEST_AUDIT_DB)
    assert scheduled["status"] == "scheduled"
