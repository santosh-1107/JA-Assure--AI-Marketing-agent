"""
Comprehensive Test Suite for Normal Content Generation Topic Flow.
Validates:
1. Mandatory topic validation (empty/whitespace blocked).
2. Prompt construction with all 8 required sections and prominent CURRENT USER REQUEST.
3. Distinct topics produce genuinely different, tailored content across brands and platforms.
4. Unsupported topics trigger clear 'Insufficient authoritative knowledge' rather than pretending unrelated RAG supports it.
5. Removal of silent hardcoded fallback demo marketing content.
6. Structured output completeness: content, brand, platform, topic, content_type, variant_id.
7. Multi-variant generation diversity in hook, structure, angle, and CTA.
8. End-to-end API generation and database persistence with compliance check.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.agents.content_agent import content_agent
from backend.services.llm_service import llm_service, MockTestProvider, LLMGenerationError
from backend.services.groq_guardrails import build_groq_user_prompt
from backend import models


@pytest.fixture(autouse=True)
def configure_test_env(monkeypatch, tmp_path):
    """Ensure clean test environment and isolated test database."""
    test_db = str(tmp_path / "test_topic_gen.db")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("JA_ASSURE_DB_PATH", test_db)
    monkeypatch.setenv("JA_ASSURE_DEMO_DB_PATH", test_db)
    from backend.database import init_db
    init_db(test_db)


# =====================================================================
# 1. MANDATORY TOPIC VALIDATION
# =====================================================================

def test_mandatory_topic_validation_in_agent():
    """Verify ContentAgent raises ValueError for empty or whitespace topic."""
    with pytest.raises(ValueError, match="Topic is mandatory and cannot be empty."):
        content_agent.generate_content(topic="", brand="Jade")

    with pytest.raises(ValueError, match="Topic is mandatory and cannot be empty."):
        content_agent.generate_content(topic="   ", brand="Jade")

    with pytest.raises(ValueError, match="Topic is mandatory and cannot be empty."):
        content_agent.generate_content(topic=None, brand="Jade")


def test_mandatory_topic_validation_in_api():
    """Verify FastAPI /content/generate returns 422 for missing or invalid topic."""
    client = TestClient(app)

    # Empty string topic
    resp1 = client.post("/content/generate", json={"brand": "Jade", "platform": "LinkedIn", "topic": ""})
    assert resp1.status_code == 422

    # Whitespace-only topic
    resp2 = client.post("/content/generate", json={"brand": "Jade", "platform": "LinkedIn", "topic": "   "})
    assert resp2.status_code == 422

    # Missing topic field
    resp3 = client.post("/content/generate", json={"brand": "Jade", "platform": "LinkedIn"})
    assert resp3.status_code == 422


# =====================================================================
# 2. PROMPT CONSTRUCTION WITH ALL REQUIRED HEADINGS
# =====================================================================

def test_prompt_construction_contains_all_required_sections():
    """Verify prompt explicitly contains all 8 required header sections."""
    prompt = build_groq_user_prompt(
        topic="High-value diamond vault custody",
        brand="Jade",
        product="Jewellers Block & Specie",
        platform="LinkedIn",
        content_type="post",
        authoritative_sources=[{"id": "doc1", "filename": "jade.pdf", "page_number": 1, "key_facts": ["Vault storage required"]}],
        competitor_intelligence={"competitors": ["Generic Insurer"], "summary": "Generic property policies"},
        historical_feedback="Avoid guaranteed cash payout claims.",
        user_directive="Highlight dual-custody safe protocols.",
    )

    required_sections = [
        "CURRENT USER REQUEST:\nHigh-value diamond vault custody",
        "BRAND:\nJade",
        "PLATFORM:\nLinkedIn",
        "CONTENT TYPE:\npost",
        "AUTHORITATIVE JA ASSURE KNOWLEDGE:",
        "RELEVANT COMPETITOR CONTEXT:",
        "PREVIOUS REVIEWER FEEDBACK:",
        "ADDITIONAL USER INSTRUCTIONS:",
    ]

    for section in required_sections:
        assert section in prompt, f"Missing required prompt section: {section}"

    # Verify primary objective header is placed before content
    assert prompt.find("=== PRIMARY GENERATION OBJECTIVE ===") < prompt.find("AUTHORITATIVE JA ASSURE KNOWLEDGE:")


# =====================================================================
# 3. DISTINCT TOPICS PRODUCE DISTINCT CONTENT
# =====================================================================

def test_distinct_topics_produce_distinct_content():
    """
    Verify three distinct topics produce genuinely distinct, specialized content:
    1. Jewellery inventory (Jade)
    2. Medical liability for doctors (DoctorShield)
    3. Courier businesses (Jade transit/courier custody)
    """
    # 1. Jewellery inventory
    t1 = "Create a LinkedIn post about protecting jewellery inventory."
    res1 = content_agent.generate_content(
        topic=t1,
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        allow_offline_fallback=True,
    )
    c1 = res1["content"]
    assert "jewell" in c1.lower() or "inventory" in c1.lower()
    assert "doctor" not in c1.lower()
    assert "medical" not in c1.lower()

    # 2. Medical liability for doctors
    t2 = "Create a LinkedIn post about medical liability for doctors."
    res2 = content_agent.generate_content(
        topic=t2,
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        allow_offline_fallback=True,
    )
    c2 = res2["content"]
    assert "medic" in c2.lower() or "doctor" in c2.lower() or "liability" in c2.lower()
    assert "diamond" not in c2.lower()
    assert "jewell" not in c2.lower()

    # 3. Courier businesses
    t3 = "Create an Instagram campaign for courier businesses."
    res3 = content_agent.generate_content(
        topic=t3,
        brand="Jade",
        platform="Instagram",
        content_type="post",
        allow_offline_fallback=True,
    )
    c3 = res3["content"]
    assert "courier" in c3.lower() or "transit" in c3.lower()

    # Verify all 3 pieces of content are mutually distinct
    assert c1 != c2
    assert c2 != c3
    assert c1 != c3


# =====================================================================
# 4. REMOVAL OF SILENT HARDCODED FALLBACK DEMO CONTENT
# =====================================================================

def test_no_silent_fallback_to_demo_content_when_llm_fails():
    """Verify system raises LLMGenerationError when LLM fails and offline fallback is disabled."""
    # Inject a failing mock provider
    failing_provider = MockTestProvider(should_fail=True)
    llm_service.set_mock_provider(failing_provider)

    try:
        with pytest.raises(LLMGenerationError):
            content_agent.generate_content(
                topic="Specialist transit protocols",
                brand="Jade",
                platform="LinkedIn",
                allow_offline_fallback=False,
            )
    finally:
        llm_service.set_mock_provider(None)


# =====================================================================
# 5. UNSUPPORTED TOPIC KNOWLEDGE HANDLING
# =====================================================================

def test_unsupported_topic_knowledge_handling():
    """Verify requesting content for an unrelated topic triggers INSUFFICIENT_KNOWLEDGE."""
    unrelated_topic = "Commercial cryptocurrency mining rig optimization"
    res = content_agent.generate_content(
        topic=unrelated_topic,
        brand="Jade",
        platform="LinkedIn",
        allow_offline_fallback=True,
    )

    assert res.get("generation_status") == "INSUFFICIENT_KNOWLEDGE"
    assert "Insufficient authoritative knowledge" in res.get("content", "")


# =====================================================================
# 6. STRUCTURED OUTPUT FIELDS
# =====================================================================

def test_structured_output_fields():
    """Verify returned dictionary contains content, brand, platform, topic, content_type, variant_id."""
    res = content_agent.generate_content(
        topic="Vault security appraisal requirements",
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        allow_offline_fallback=True,
    )

    required_fields = ["content", "brand", "platform", "topic", "content_type", "variant_id"]
    for field in required_fields:
        assert field in res, f"Missing required output field: {field}"

    assert res["topic"] == "Vault security appraisal requirements"
    assert res["brand"] == "Jade"
    assert res["platform"] == "LinkedIn"
    assert res["content_type"] == "post"
    assert res["variant_id"].startswith("var-")


# =====================================================================
# 7. MULTIPLE VARIANT DIVERSITY
# =====================================================================

def test_multiple_variant_diversity():
    """Verify requesting multiple variants produces distinct angles and content."""
    res = content_agent.generate_content(
        topic="Protecting high-value inventory in transit",
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        allow_offline_fallback=True,
        num_variants=3,
    )

    assert "variants" in res
    variants = res["variants"]
    assert len(variants) == 3

    # Check distinct variant IDs
    v_ids = [v["variant_id"] for v in variants]
    assert len(set(v_ids)) == 3

    # Check distinct copy content across angles
    v_contents = [v["content"] for v in variants]
    assert len(set(v_contents)) == 3

    # Verify each variant has an angle definition
    for v in variants:
        assert "angle" in v and len(v["angle"]) > 0


# =====================================================================
# 8. API GENERATION ENDPOINT END-TO-END FLOW
# =====================================================================

def test_api_generation_endpoint_flow():
    """Verify end-to-end API generation, database insertion, and compliance evaluation."""
    client = TestClient(app)
    req = {
        "brand": "DoctorShield",
        "platform": "LinkedIn",
        "content_type": "post",
        "topic": "Clinical risk governance and legal defense financing",
        "allow_offline_fallback": True,
    }

    resp = client.post("/content/generate", json=req)
    assert resp.status_code == 201
    data = resp.json()

    assert data["topic"] == req["topic"]
    assert data["brand"] == "DoctorShield"
    assert data["status"] == "pending"
    assert "compliance_result" in data
    assert "variant_id" in data

    # Verify persisted in SQLite database
    persisted = models.get_content_by_id(data["id"])
    assert persisted is not None
    assert persisted["topic"] == req["topic"]
    assert persisted["brand"] == "DoctorShield"
