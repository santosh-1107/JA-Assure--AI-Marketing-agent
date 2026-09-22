"""
Compliance Gate Component for JA Assure.
Provides clear governance status indicators, violated rule analysis, and policy checks.
"""

from typing import Any, Dict, List


def format_compliance_box(comp_result: Dict[str, Any]) -> str:
    """
    Renders the governance-compliant HTML block:
    - FAIL box: red alert block with risk score, risk level, rule pills, and specific reasons
    - PASS box: green verified block with risk score, low risk level, and policy checks
    """
    comp = comp_result or {"status": "pass", "reasons": []}
    is_fail = (comp.get("status") == "fail")

    risk_score = comp.get("risk_score")
    if risk_score is None:
        risk_score = 60.0 if is_fail else 0.0
    risk_level = comp.get("risk_level") or ("HIGH" if is_fail else "LOW")

    level_bg = "#FEF2F2" if risk_level == "HIGH" else ("#FFFBEB" if risk_level == "MEDIUM" else "#F0FDF4")
    level_color = "#DC2626" if risk_level == "HIGH" else ("#D97706" if risk_level == "MEDIUM" else "#16A34A")

    if is_fail:
        reasons = comp.get("reasons", [])
        rules_html = ""
        for r in reasons:
            rule_name = r.get("rule", "POLICY_VIOLATION")
            msg = r.get("message", "Non-compliant terminology identified.")
            rules_html += f'<div style="margin-top: 0.35rem;"><span class="violation-pill">{rule_name}</span><div class="violation-reason">{msg}</div></div>'
        return (
            f'<div class="compliance-gate-box box-fail">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">'
            f'<span class="gate-status-text-fail">❌ FAIL — COMPLIANCE GATE</span>'
            f'<span style="background: {level_bg}; color: {level_color}; font-size: 0.68rem; font-weight: 800; padding: 0.15rem 0.4rem; border-radius: 4px;">'
            f'{risk_level} ({risk_score:.0f}/100)</span>'
            f'</div>'
            f'<div style="font-size: 0.70rem; font-weight: 700; color: #991B1B;">Violated Rules:</div>'
            f'{rules_html}</div>'
        )
    else:
        return (
            f'<div class="compliance-gate-box box-pass">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">'
            f'<span class="gate-status-text-pass">✔ PASS — COMPLIANT</span>'
            f'<span style="background: {level_bg}; color: {level_color}; font-size: 0.68rem; font-weight: 800; padding: 0.15rem 0.4rem; border-radius: 4px;">'
            f'LOW RISK ({risk_score:.0f}/100)</span>'
            f'</div>'
            f'<div style="font-size: 0.74rem; color: #166534; line-height: 1.55;">'
            f'<div>✔ Zero regulatory violations</div>'
            f'<div>✔ Mandatory qualifiers present</div>'
            f'<div>✔ Grounded in official JA Assure knowledge</div>'
            f'<div>✔ Ready for human approval</div></div></div>'
        )

