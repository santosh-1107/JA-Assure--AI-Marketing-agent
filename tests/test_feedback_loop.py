"""
End-to-End Feedback Loop Test for JA Assure AI Marketing Agent.
Implements and verifies the exact 10-step hackathon demo flow:
1. Generate content containing 'guaranteed payout'.
2. Compliance Agent returns FAIL.
3. Reviewer rejects it.
4. Reviewer adds tag='inaccurate_claim', note='Avoid guaranteed payout language.'
5. Feedback is stored.
6. Regenerate.
7. New generation receives the feedback.
8. New content avoids the problematic claim.
9. Compliance Agent checks it.
10. Result is compliant (PASS) and shows learning evidence.
"""

import os
import pytest
from pathlib import Path

from backend.database import init_db
from backend import models
from backend.agents.content_agent import ContentAgent
from backend.agents.compliance_agent import ComplianceAgent
from backend.agents.feedback_agent import FeedbackAgent
from backend.agents.research_agent import research_agent
from backend.knowledge.knowledge_retriever import knowledge_retriever

TEST_DB_PATH = str(Path(__file__).resolve().parent / "test_feedback_loop.db")


@pytest.fixture(autouse=True)
def setup_teardown_db(monkeypatch):
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", TEST_DB_PATH)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


def test_the_complete_10_step_feedback_learning_loop():
    content_agent = ContentAgent()
    compliance_agent = ComplianceAgent()
    feedback_agent = FeedbackAgent(db_path=TEST_DB_PATH)

    brand = "Jade"
    platform = "LinkedIn"
    topic = "Family financial protection"

    # STEP 1: Generate initial content (with force_trigger_flaw=True for first demo cycle)
    initial_draft = content_agent.generate(
        topic=topic,
        brand=brand,
        platform=platform,
        content_type="post",
        force_trigger_flaw=True,
        cycle=1,
    )
    assert "guaranteed payout" in initial_draft["content"].lower()

    # STEP 2: Compliance Agent checks initial content -> returns FAIL
    initial_compliance = compliance_agent.check(
        content=initial_draft["content"],
        brand=brand,
    )
    assert initial_compliance["status"] == "fail"
    rules = [r["rule"] for r in initial_compliance["reasons"]]
    assert "NO_GUARANTEED_PAYOUT" in rules

    # Store in database with status='pending'
    item = models.insert_content(
        brand=brand,
        platform=platform,
        content_type="post",
        content=initial_draft["content"],
        compliance_result=initial_compliance,
        cycle=1,
        status="pending",
        db_path=TEST_DB_PATH,
    )
    assert item["status"] == "pending"

    # STEP 3 & 4: Reviewer rejects item, adds tag='inaccurate_claim' and note
    rejection_tag = "inaccurate_claim"
    rejection_note = "Avoid guaranteed payout language. Always qualify claims with 'subject to policy terms and conditions'."

    rejected_item = models.reject_content(
        content_id=item["id"],
        tag=rejection_tag,
        note=rejection_note,
        db_path=TEST_DB_PATH,
    )
    assert rejected_item["status"] == "rejected"

    # STEP 5: Feedback is stored and retrievable
    stored_feedback = feedback_agent.get_recent_feedback(brand=brand, n=5)
    assert len(stored_feedback) >= 1
    assert stored_feedback[0]["tag"] == rejection_tag
    assert "Avoid guaranteed payout" in stored_feedback[0]["note"]

    # STEP 6 & 7: Regenerate with feedback injected
    # Verify the new prompt actually contains the stored feedback
    prompt_text = content_agent._build_user_prompt(
        topic, platform, "post", feedback_agent.format_feedback_for_prompt(stored_feedback)
    )
    assert "Avoid guaranteed payout language" in prompt_text
    assert "INACCURATE_CLAIM" in prompt_text

    # Content Agent receives the stored feedback
    regenerated_draft = content_agent.generate(
        topic=topic,
        brand=brand,
        platform=platform,
        content_type="post",
        past_corrections=stored_feedback,
        force_trigger_flaw=False,  # Feedback learning resolves the flaw
        cycle=2,
    )

    # STEP 8: New content explicitly avoids the problematic claim
    regenerated_text = regenerated_draft["content"]
    assert "guaranteed payout" not in regenerated_text.lower()
    assert "100% protected" not in regenerated_text.lower()
    assert "subject to policy terms" in regenerated_text.lower() and "conditions" in regenerated_text.lower()

    # STEP 9: Compliance Agent checks regenerated content -> returns PASS
    regenerated_compliance = compliance_agent.check(
        content=regenerated_text,
        brand=brand,
    )
    assert regenerated_compliance["status"] == "pass"
    assert len(regenerated_compliance["reasons"]) == 0

    # Store regenerated variant linked to parent_id
    new_item = models.insert_content(
        brand=brand,
        platform=platform,
        content_type="post",
        content=regenerated_text,
        compliance_result=regenerated_compliance,
        cycle=2,
        parent_id=item["id"],
        fixed_issue=f"Applied reviewer correction: [{rejection_tag}] {rejection_note}",
        status="pending",
        db_path=TEST_DB_PATH,
    )

    # STEP 10: Before / After comparison verifies visible learning
    pairs = models.get_before_after_pairs(brand=brand, db_path=TEST_DB_PATH)
    assert len(pairs) >= 1
    pair = pairs[0]
    assert pair["parent_id"] == item["id"]
    assert pair["child_id"] == new_item["id"]
    assert "guaranteed payout" in pair["original_content"].lower()
    assert "guaranteed payout" not in pair["regenerated_content"].lower()
    assert pair["child_compliance"]["status"] == "pass"
    assert pair["feedback_tag"] == rejection_tag


def test_brand_voice_differentiation_same_topic():
    """
    Verify that generating the same topic for Jade vs DoctorShield produces
    visibly distinct brand voices that do not sound identical.
    """
    content_agent = ContentAgent()
    topic = "Risk management and liability safeguarding"

    jade_draft = content_agent.generate(
        topic=topic,
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        force_trigger_flaw=False,
        cycle=2,
    )

    doctorshield_draft = content_agent.generate(
        topic=topic,
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        force_trigger_flaw=False,
        cycle=2,
    )

    jade_text = jade_draft["content"].lower()
    ds_text = doctorshield_draft["content"].lower()

    # Content must not be identical
    assert jade_text != ds_text

    # Jade must have luxury / wealth / heirloom vocabulary
    assert any(term in jade_text for term in ["heirloom", "jewelry", "jewellery", "wealth", "bespoke", "private client"])
    # Jade must NOT sound clinical
    assert "malpractice" not in jade_text
    assert "smc" not in jade_text

    # DoctorShield must have clinical / medical defense vocabulary
    assert any(term in ds_text for term in ["clinical", "medico-legal", "indemnity", "practitioner", "physician", "doctor"])
    # DoctorShield must NOT discuss luxury heirlooms
    assert "heirloom" not in ds_text
    assert "diamond" not in ds_text


def test_knowledge_retriever_grounding():
    """Verify lightweight knowledge retriever matches brand and topic to official JA Assure articles."""
    # Jade / Jewellers Block topic
    jade_sources = knowledge_retriever.retrieve(
        brand="Jade",
        topic="How jewellery businesses protect high-value inventory",
        top_k=2,
    )
    assert len(jade_sources) >= 1
    assert jade_sources[0]["id"] == "jewellers_block"
    assert "Jewellers Block" in jade_sources[0]["title"]
    assert "https://www.ja-assure.com/blog-jewellers-block.html" == jade_sources[0]["url"]
    assert any("commercial trade" in fact.lower() for fact in jade_sources[0]["key_facts"])

    # DoctorShield / Medical Indemnity topic
    ds_sources = knowledge_retriever.retrieve(
        brand="DoctorShield",
        topic="Medical indemnity and malpractice defense for healthcare professionals",
        top_k=2,
    )
    assert len(ds_sources) >= 1
    assert ds_sources[0]["id"] == "medical_indemnity"
    assert "Medical Indemnity" in ds_sources[0]["title"]
    assert "https://www.ja-assure.com/blog-medical-malpractice.html" == ds_sources[0]["url"]
    assert any("dual function" in fact.lower() for fact in ds_sources[0]["key_facts"])


def test_research_agent_contract():
    """Verify Research Agent output schema: {summary, changes, recommendation, sources}."""
    result = research_agent.research(
        brand="Jade",
        topic="How jewellery businesses protect high-value inventory",
    )
    assert "summary" in result
    assert "changes" in result
    assert "recommendation" in result
    assert "sources" in result
    assert len(result["sources"]) >= 1

    primary_source = result["sources"][0]
    assert primary_source["title"] == "Jewellers Block and Specie Insurance: Protecting the World's Most Precious Assets"
    assert primary_source["url"] == "https://www.ja-assure.com/blog-jewellers-block.html"
    assert len(primary_source["key_facts"]) > 0


def test_content_agent_knowledge_grounding_and_sources():
    """Verify generated assets retain knowledge sources metadata with official JA Assure URLs."""
    content_agent = ContentAgent()

    # Generate Jade post
    jade_gen = content_agent.generate(
        topic="How jewellery businesses protect high-value inventory",
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        force_trigger_flaw=False,
        cycle=2,
    )
    assert "sources" in jade_gen
    assert len(jade_gen["sources"]) >= 1
    assert any("ja-assure.com" in s["url"] for s in jade_gen["sources"])
    assert any(term in jade_gen["content"].lower() for term in ["jewellers block", "jeweller's block", "block coverage", "specie", "jewellery"])

    # Generate DoctorShield post
    ds_gen = content_agent.generate(
        topic="Medical indemnity and clinical malpractice defense",
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        force_trigger_flaw=False,
        cycle=2,
    )
    assert "sources" in ds_gen
    assert len(ds_gen["sources"]) >= 1
    assert any("ja-assure.com" in s["url"] for s in ds_gen["sources"])
    assert "indemnity" in ds_gen["content"].lower() and "medical" in ds_gen["content"].lower()


def test_anti_hallucination_system_instruction():
    """Verify Content Agent system instruction explicitly mandates anti-hallucination behavior."""
    content_agent = ContentAgent()
    sys_inst = content_agent._build_system_instruction(
        brand="Jade",
        voice={"tone": "Professional", "persona": "InsurTech advisor"},
        platform="LinkedIn",
        platform_guides={},
    )
    assert "ANTI-HALLUCINATION" in sys_inst
    assert "Use only the provided company knowledge for specific JA Assure product facts" in sys_inst
    assert "NEVER invent" in sys_inst
    assert "Coverage limits" in sys_inst
    assert "Claim settlement guarantees" in sys_inst
    assert "Market rankings" in sys_inst


def test_end_to_end_knowledge_grounded_judge_flow():
    """
    Simulates the complete judge demo flow:
    1. Select Jade
    2. Enter topic: 'How jewellery businesses protect high-value inventory'
    3. Research Agent retrieves Jewellers Block knowledge
    4. Content Agent generates risky LinkedIn post
    5. Compliance Gate flags it (FAIL)
    6. Reviewer rejects with inaccurate_claim
    7. Stored in feedback
    8. Regenerate with feedback & Jewellers Block knowledge
    9. Compliance Gate PASS
    10. Verify sources metadata and Before/After learning
    """
    content_agent = ContentAgent()
    compliance_agent = ComplianceAgent()
    topic = "How jewellery businesses protect high-value inventory"

    # 1 & 2 & 3. Research official knowledge
    research_ctx = research_agent.research(brand="Jade", topic=topic)
    assert any("jewellers_block" in s.get("url", "") or "jewellers" in s.get("title", "").lower() for s in research_ctx["sources"])

    # 4. Generate initial risky post
    initial_gen = content_agent.generate(
        topic=topic,
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        research_context=research_ctx,
        force_trigger_flaw=True,
        cycle=1,
    )

    # 5. Compliance Gate evaluates -> FAIL
    comp_1 = compliance_agent.check(initial_gen["content"], "Jade")
    assert comp_1["status"] == "fail"

    # Store in DB
    item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=initial_gen["content"],
        compliance_result=comp_1,
        cycle=1,
        sources=initial_gen["sources"],
        status="pending",
        db_path=TEST_DB_PATH,
    )

    # 6 & 7. Reviewer rejects with inaccurate_claim
    models.reject_content(
        content_id=item["id"],
        tag="inaccurate_claim",
        note="Cannot promise guaranteed payouts or 100% loss-free protection on jewellery inventory. Must qualify under policy terms and vault security criteria.",
        db_path=TEST_DB_PATH,
    )

    # 8. Regenerate with feedback
    fb_list = FeedbackAgent(db_path=TEST_DB_PATH).get_recent_feedback("Jade", n=5)
    regen = content_agent.generate(
        topic=topic,
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        research_context=research_ctx,
        past_corrections=fb_list,
        force_trigger_flaw=False,
        cycle=2,
    )

    # 9. Compliance Gate evaluates -> PASS
    comp_2 = compliance_agent.check(regen["content"], "Jade")
    assert comp_2["status"] == "pass"
    assert len(comp_2["reasons"]) == 0

    # 10. Store regenerated item
    new_item = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=regen["content"],
        compliance_result=comp_2,
        cycle=2,
        parent_id=item["id"],
        fixed_issue="Avoided guaranteed payout claim; qualified coverage under official policy terms.",
        sources=regen["sources"],
        status="pending",
        db_path=TEST_DB_PATH,
    )

    # Verify source attribution persists in DB
    retrieved_item = models.get_content_by_id(new_item["id"], db_path=TEST_DB_PATH)
    assert retrieved_item["sources"] is not None
    assert len(retrieved_item["sources"]) >= 1
    assert "ja-assure.com" in retrieved_item["sources"][0]["url"]

