"""
Unit tests for the Compliance Agent and insurance marketing rubrics.
"""

import pytest
from backend.agents.compliance_agent import ComplianceAgent

@pytest.fixture
def compliance_agent():
    return ComplianceAgent()


def test_jade_compliant_copy_passes(compliance_agent):
    """Verify compliant Jade copy receives PASS verdict."""
    content = (
        "Safeguarding multi-generational heirlooms requires more than standard coverage. "
        "At Jade, our bespoke policies offer private client valuation and structured claims assessment — "
        "subject to policy terms and conditions and underwriter schedule."
    )
    result = compliance_agent.check(content=content, brand="Jade")
    assert result["status"] == "pass"
    assert len(result["reasons"]) == 0


def test_jade_guaranteed_payout_fails(compliance_agent):
    """Verify guaranteed payout claim triggers NO_GUARANTEED_PAYOUT rule."""
    content = "Jade offers instant guaranteed payouts for any lost jewelry, no questions asked!"
    result = compliance_agent.check(content=content, brand="Jade")
    assert result["status"] == "fail"
    rules_triggered = [r["rule"] for r in result["reasons"]]
    assert "NO_GUARANTEED_PAYOUT" in rules_triggered
    # Verify non-vague descriptive message
    assert any("guaranteed" in r["message"].lower() for r in result["reasons"])


def test_jade_absolute_protection_fails(compliance_agent):
    """Verify '100% protected' triggers NO_GUARANTEED_PROTECTION rule."""
    content = "Your diamond collection is 100% protected with zero risk under our policy."
    result = compliance_agent.check(content=content, brand="Jade")
    assert result["status"] == "fail"
    rules_triggered = [r["rule"] for r in result["reasons"]]
    assert "NO_GUARANTEED_PROTECTION" in rules_triggered


def test_doctorshield_guaranteed_dismissal_fails(compliance_agent):
    """Verify DoctorShield flags guaranteed dismissal of malpractice suits."""
    content = "DoctorShield provides guaranteed dismissal for all malpractice lawsuits."
    result = compliance_agent.check(content=content, brand="DoctorShield")
    assert result["status"] == "fail"
    rules_triggered = [r["rule"] for r in result["reasons"]]
    assert "NO_GUARANTEED_LEGAL_OUTCOME" in rules_triggered


def test_doctorshield_fearmongering_fails(compliance_agent):
    """Verify aggressive scare tactics are flagged as inappropriate sales language."""
    content = "Patients will sue you tomorrow! Act now or face total financial ruin."
    result = compliance_agent.check(content=content, brand="DoctorShield")
    assert result["status"] == "fail"
    rules_triggered = [r["rule"] for r in result["reasons"]]
    assert "INAPPROPRIATE_SALES_LANGUAGE" in rules_triggered


def test_off_brand_tone_detected(compliance_agent):
    """Verify cross-brand tone violation (e.g. Jade discussing medical malpractice)."""
    content = "Jade provides doctors with medical malpractice indemnity and clinical negligence defense."
    result = compliance_agent.check(content=content, brand="Jade")
    assert result["status"] == "fail"
    rules_triggered = [r["rule"] for r in result["reasons"]]
    assert "OFF_BRAND_TONE" in rules_triggered


def test_malformed_llm_json_safety(compliance_agent, monkeypatch):
    """Verify that if the LLM returns invalid or malformed JSON, the system does not crash."""
    from backend.gemini_service import gemini_service
    monkeypatch.setattr(gemini_service, "is_live", True)
    monkeypatch.setattr(gemini_service, "generate_text", lambda *args, **kwargs: "MALFORMED {NOT JSON")

    # Should safely return fallback pass or deterministic check without throwing an unhandled exception
    res = compliance_agent.check(
        content="Bespoke private jewelry advisory, subject to policy terms and conditions.",
        brand="Jade",
    )
    assert res["status"] in ("pass", "fail")
    assert isinstance(res["reasons"], list)
