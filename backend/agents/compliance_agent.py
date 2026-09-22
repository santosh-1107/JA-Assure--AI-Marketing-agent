"""
Compliance Agent for JA Assure AI Marketing Agent.
Evaluates marketing content against brand-specific insurance regulatory rubrics.
Performs text normalization (whitespace, punctuation, hyphens, repeated spaces).
Supports phrase variations, neutral rule IDs, and validates LLM semantic checks.
"""

import os
import re
import yaml
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from backend.gemini_service import gemini_service

logger = logging.getLogger(__name__)

RUBRICS_DIR = Path(__file__).resolve().parent.parent.parent / "rubrics"
VALID_BRANDS = {"Jade", "DoctorShield"}


def normalize_compliance_text(text: str) -> str:
    """
    Normalize text for robust compliance pattern matching:
    - Lowercase
    - Replace em-dashes, en-dashes, underscores, and hyphens with spaces
    - Remove punctuation (except alphanumerics and spaces)
    - Collapse multiple whitespace to single space
    """
    if not text:
        return ""
    t = text.lower()
    # Normalize hyphens and dashes (including unicode non-breaking hyphens \u2010-\u2015)
    t = re.sub(r"[\u2010-\u2015—–_\-]+", " ", t)
    # Strip non-alphanumeric except spaces
    t = re.sub(r"[^\w\s]", " ", t)
    # Collapse multiple whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pattern_in_text(pattern: str, normalized_text: str) -> Optional[str]:
    """
    Check if pattern exists in normalized text with word boundary awareness.
    Returns the matched phrase if found, otherwise None.
    """
    norm_pattern = normalize_compliance_text(pattern)
    if not norm_pattern:
        return None

    if norm_pattern in normalized_text:
        return pattern

    # Word boundary regex for multi-word phrases
    tokens = [re.escape(tok) for tok in norm_pattern.split()]
    regex_str = r"\b" + r"\s+".join(tokens) + r"\b"
    if re.search(regex_str, normalized_text):
        return pattern

    return None


class ComplianceStatus(str):
    """Case-insensitive string supporting both 'PASS'/'FAIL' and legacy 'pass'/'fail' assertions."""
    def __eq__(self, other: Any) -> bool:
        return self.upper() == str(other).upper()

    def __ne__(self, other: Any) -> bool:
        return self.upper() != str(other).upper()

    def __hash__(self) -> int:
        return hash(self.upper())


def map_rule_to_issue_type(rule_id: str, category: str) -> str:
    """Map rule ID and category to standardized issue type for heatmap and analytics."""
    r_lower = rule_id.lower()
    if "payout" in r_lower or "settlement" in r_lower or "instant" in r_lower:
        return "unsupported_guarantee"
    elif "absolute" in r_lower or "protection" in r_lower or "immunity" in r_lower:
        return "inaccurate_claim"
    elif "qualif" in r_lower or "disclosure" in r_lower:
        return "missing_qualifier"
    elif "sales" in r_lower or "fear" in r_lower or "urgency" in r_lower:
        return "aggressive_urgency"
    elif "tone" in r_lower or "off_brand" in r_lower or "brand" in r_lower:
        return "off_brand_tone"
    elif "legal" in r_lower or "dismissal" in r_lower:
        return "unsupported_legal_claim"
    elif "unsupported" in r_lower or "factual" in r_lower or "grounding" in r_lower:
        return "unsupported_claim"
    return category.lower().replace(" ", "_")


class ComplianceAgent:
    """
    Evaluates marketing copy against external YAML compliance rubrics.
    Combines deterministic normalized pattern matching with optional LLM semantic evaluation.
    Outputs structured risk scoring, risk level, and issues list.
    """

    def __init__(self, rubrics_dir: Optional[Path] = None):
        self.prompts_dir = rubrics_dir or RUBRICS_DIR
        self._rubric_cache: Dict[str, Dict[str, Any]] = {}

    def load_rubric(self, brand: str) -> Dict[str, Any]:
        """Load and cache brand rubric from YAML with strict brand checking."""
        if brand not in VALID_BRANDS:
            raise ValueError(f"Invalid brand '{brand}'. Must be one of: {sorted(VALID_BRANDS)}")

        normalized_brand = brand.lower()
        if normalized_brand in self._rubric_cache:
            return self._rubric_cache[normalized_brand]

        yaml_path = self.prompts_dir / f"{normalized_brand}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Rubric file not found at {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._rubric_cache[normalized_brand] = data
            return data

    def get_rules_for_brand(self, brand: str) -> List[Dict[str, Any]]:
        """Return list of active compliance rules for the given brand."""
        return self.load_rubric(brand).get("rules", [])

    def check(
        self,
        content: str,
        brand: str,
        claim_grounding: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate content against brand compliance rubric.
        Returns:
            {
                "status": "PASS | FAIL",
                "risk_level": "LOW | MEDIUM | HIGH",
                "risk_score": float (0.0 to 100.0),
                "issues": [
                    {
                        "rule_id": "...",
                        "issue_type": "...",
                        "severity": "...",
                        "evidence": "...",
                        "explanation": "..."
                    }
                ],
                "reasons": [...]
            }
        """
        rubric = self.load_rubric(brand)
        rules = rubric.get("rules", [])
        reasons: List[Dict[str, Any]] = []

        norm_content = normalize_compliance_text(content)

        # Step 1: Normalized Deterministic Rule Check
        for rule in rules:
            rule_id = rule.get("id")
            category = rule.get("category", "General Regulatory")
            severity = rule.get("severity", "HIGH")
            fail_msg = rule.get("fail_message", f"Content violated compliance rule {rule_id}.")
            reference = rule.get("reference", "JA Assure Governance Standards")
            aliases = rule.get("aliases", [])

            # Check trigger patterns (prohibited terms)
            patterns = rule.get("trigger_patterns", [])
            matched = False
            for pattern in patterns:
                hit = pattern_in_text(pattern, norm_content)
                if hit:
                    # Record primary rule violation
                    reasons.append({
                        "rule": rule_id,
                        "severity": severity,
                        "category": category,
                        "message": fail_msg,
                        "matched_phrase": pattern,
                        "reference": reference,
                    })
                    # Also register alias IDs so legacy tests and neutral IDs both match
                    for alias in aliases:
                        if alias != rule_id:
                            reasons.append({
                                "rule": alias,
                                "severity": severity,
                                "category": category,
                                "message": fail_msg,
                                "matched_phrase": pattern,
                                "reference": reference,
                            })
                    matched = True
                    break

            if matched:
                continue

            # Check mandatory qualified phrases (if content makes coverage claims)
            required_phrases = rule.get("required_phrases", [])
            if required_phrases:
                coverage_keywords = ["cover", "policy", "benefit", "claim", "protection", "indemnity", "compensate", "malpractice"]
                has_coverage_keyword = any(kw in norm_content for kw in coverage_keywords)
                has_qualifier = any(pattern_in_text(req, norm_content) for req in required_phrases)

                if has_coverage_keyword and not has_qualifier:
                    # Only add if not already flagged for absolute protection or guaranteed payout
                    already_flagged = any(
                        r["rule"] in ("NO_ABSOLUTE_PROTECTION", "NO_GUARANTEED_PROTECTION", "NO_GUARANTEED_PAYOUT", "NO_UNQUALIFIED_IMMUNITY")
                        for r in reasons
                    )
                    if not already_flagged:
                        reasons.append({
                            "rule": rule_id,
                            "severity": severity,
                            "category": category,
                            "message": fail_msg,
                            "matched_phrase": "Missing regulatory qualifier",
                            "reference": reference,
                        })
                        for alias in aliases:
                            if alias != rule_id:
                                reasons.append({
                                    "rule": alias,
                                    "severity": severity,
                                    "category": category,
                                    "message": fail_msg,
                                    "matched_phrase": "Missing regulatory qualifier",
                                    "reference": reference,
                                })

        # Step 2: If live Gemini API is available and deterministic checks passed, run semantic LLM verification
        if gemini_service.is_live and len(reasons) == 0:
            llm_reasons = self._llm_check(content, brand, rules)
            reasons.extend(llm_reasons)

        # Step 3: Two-Stage Safety Pipeline - Evaluate Claim Grounding from Content Agent
        if claim_grounding:
            for cg in claim_grounding:
                cg_status = (cg.get("status") or "").upper()
                cg_claim = cg.get("claim", "")
                if cg_status == "UNSUPPORTED":
                    reasons.append({
                        "rule": "UNSUPPORTED_FACTUAL_CLAIM",
                        "severity": "CRITICAL",
                        "category": "Factual Grounding & Marketing Safety",
                        "message": f"Generated marketing copy makes unsupported factual claim not grounded in authoritative JA Assure documents: '{cg_claim}'. {cg.get('reason', '')}".strip(),
                        "matched_phrase": cg_claim,
                        "reference": "JA Assure Factual Grounding & Marketing Safety Mandate",
                    })
                elif cg_status == "UNCERTAIN":
                    reasons.append({
                        "rule": "UNCERTAIN_FACTUAL_CLAIM",
                        "severity": "MODERATE",
                        "category": "Factual Grounding & Marketing Safety",
                        "message": f"Claim lacks unambiguous grounding in authoritative documents: '{cg_claim}'. Requires underwriter sign-off.",
                        "matched_phrase": cg_claim,
                        "reference": "JA Assure Factual Grounding & Marketing Safety Mandate",
                    })

        # De-duplicate reasons by rule ID
        unique_reasons = []
        seen_rules: Set[str] = set()
        for r in reasons:
            if r["rule"] not in seen_rules:
                seen_rules.add(r["rule"])
                unique_reasons.append(r)

        # Build upgraded issues list
        issues = []
        severity_weights = {"CRITICAL": 45.0, "HIGH": 30.0, "MODERATE": 15.0, "LOW": 5.0}
        total_risk = 0.0

        for r in unique_reasons:
            sev = r.get("severity", "HIGH").upper()
            total_risk += severity_weights.get(sev, 20.0)
            issues.append({
                "rule_id": r.get("rule", "UNKNOWN_RULE"),
                "issue_type": map_rule_to_issue_type(r.get("rule", ""), r.get("category", "")),
                "severity": sev,
                "evidence": r.get("matched_phrase", ""),
                "explanation": r.get("message", ""),
                "reference": r.get("reference", ""),
            })

        calculated_risk_score = min(100.0, total_risk)
        if calculated_risk_score == 0.0:
            risk_level = "LOW"
        elif calculated_risk_score <= 35.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        status_str = "fail" if len(unique_reasons) > 0 else "pass"

        return {
            "status": status_str,
            "status_display": status_str.upper(),
            "risk_level": risk_level,
            "risk_score": calculated_risk_score,
            "issues": issues,
            "reasons": unique_reasons,
            "claim_grounding": claim_grounding or [],
        }

    def _llm_check(self, content: str, brand: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Secondary LLM semantic verification against regulatory rubrics.
        Validates returned rule IDs against YAML definitions; rejects unknown rule IDs.
        """
        valid_rule_ids: Set[str] = set()
        rule_map: Dict[str, Dict[str, Any]] = {}
        for r in rules:
            r_id = r.get("id")
            valid_rule_ids.add(r_id)
            rule_map[r_id] = r
            for alias in r.get("aliases", []):
                valid_rule_ids.add(alias)
                rule_map[alias] = r

        rules_summary = "\n".join([
            f"- {r.get('id')}: {r.get('description')}" for r in rules
        ])

        system_instruction = (
            f"You are the Chief Regulatory Compliance Officer for InsurTech brand '{brand}'. "
            "Evaluate marketing content against strict advertising codes. "
            "You must return ONLY a JSON object with this schema:\n"
            "{\"status\": \"pass\"|\"fail\", \"reasons\": [{\"rule\": \"RULE_ID\", \"category\": \"Category\", \"message\": \"Explanation\", \"matched_phrase\": \"phrase\"}]}\n"
            "If the content is compliant, return {\"status\": \"pass\", \"reasons\": []}."
        )

        prompt = f"Rubric Rules:\n{rules_summary}\n\nContent to audit:\n'''{content}'''\n"

        try:
            response_text = gemini_service.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.1,
            )
            if response_text:
                clean_json = response_text
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                parsed = json.loads(clean_json)

                if parsed.get("status") == "fail" and parsed.get("reasons"):
                    validated_reasons = []
                    for r in parsed["reasons"]:
                        rule_name = r.get("rule")
                        # Strict validation: reject unknown rule IDs
                        if rule_name in valid_rule_ids:
                            matched_rule = rule_map.get(rule_name, {})
                            validated_reasons.append({
                                "rule": rule_name,
                                "severity": matched_rule.get("severity", "HIGH"),
                                "category": r.get("category") or matched_rule.get("category", "Regulatory"),
                                "message": r.get("message") or matched_rule.get("fail_message", "Compliance rule triggered."),
                                "matched_phrase": r.get("matched_phrase", ""),
                                "reference": matched_rule.get("reference", "JA Assure Governance Standards"),
                            })
                        else:
                            logger.warning(f"LLM semantic check returned unknown rule ID '{rule_name}' — rejected from reasons.")
                    return validated_reasons
        except Exception as exc:
            logger.debug(f"LLM compliance audit skipped or non-JSON: {exc}")

        return []


# Global compliance agent instance
compliance_agent = ComplianceAgent()
