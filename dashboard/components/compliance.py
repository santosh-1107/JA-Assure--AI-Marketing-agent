"""
Compliance Gate Component for JA Assure.
Provides clear governance status indicators, violated rule analysis, and policy checks.
"""

from typing import Any, Dict, List


def format_compliance_box(comp_result: Dict[str, Any]) -> str:
    """
    Renders the governance-compliant HTML block matching the reference image:
    - FAIL box: red alert block with rule pills and specific reasons
    - PASS box: green verified block with policy checks
    """
    comp = comp_result or {"status": "pass", "reasons": []}
    is_fail = (comp.get("status") == "fail")

    if is_fail:
        reasons = comp.get("reasons", [])
        rules_html = ""
        for r in reasons:
            rule_name = r.get("rule", "POLICY_VIOLATION")
            msg = r.get("message", "Non-compliant terminology identified.")
            rules_html += f'<div style="margin-top: 0.35rem;"><span class="violation-pill">{rule_name}</span><div class="violation-reason">{msg}</div></div>'
        return f'<div class="compliance-gate-box box-fail"><div class="gate-status-text-fail">❌ FAIL — COMPLIANCE GATE</div><div style="font-size: 0.70rem; font-weight: 700; color: #991B1B;">Violated Rules:</div>{rules_html}</div>'
    else:
        return '<div class="compliance-gate-box box-pass"><div class="gate-status-text-pass">✔ PASS — COMPLIANT</div><div style="font-size: 0.74rem; color: #166534; line-height: 1.55;"><div>✔ No compliance violations</div><div>✔ On-brand messaging</div><div>✔ Appropriate language</div><div>✔ Ready for human approval</div></div></div>'
