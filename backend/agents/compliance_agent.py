"""
Compliance Agent for JA Assure AI Marketing Agent.
Evaluates marketing content against brand-specific insurance regulatory rubrics.
Identifies exact rule infractions (e.g. MAS insurance advertising prohibitions).
"""

import os
import re
import yaml
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.gemini_service import gemini_service

logger = logging.getLogger(__name__)

RUBRICS_DIR = Path(__file__).resolve().parent.parent.parent / "rubrics"


class ComplianceAgent:
    """
    Evaluates marketing copy against external YAML compliance rubrics.
    Combines deterministic pattern matching with optional LLM semantic evaluation.
    """

    def __init__(self, rubrics_dir: Optional[Path] = None):
        self.rubrics_dir = rubrics_dir or RUBRICS_DIR
        self._rubric_cache: Dict[str, Dict[str, Any]] = {}

    def load_rubric(self, brand: str) -> Dict[str, Any]:
        """Load and cache brand rubric from YAML."""
        normalized_brand = "jade" if "jade" in brand.lower() else "doctorshield"
        if normalized_brand in self._rubric_cache:
            return self._rubric_cache[normalized_brand]

        yaml_path = self.rubrics_dir / f"{normalized_brand}.yaml"
        if not yaml_path.exists():
            logger.warning(f"Rubric file not found at {yaml_path}, loading fallback rules.")
            return {"brand": brand, "rules": []}

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._rubric_cache[normalized_brand] = data
            return data

    def check(self, content: str, brand: str) -> Dict[str, Any]:
        """
        Evaluate content against brand compliance rubric.
        Returns:
            {
                "status": "pass" | "fail",
                "reasons": [
                    {
                        "rule": "RULE_ID",
                        "category": "Regulatory Category",
                        "message": "Detailed explanation",
                        "matched_phrase": "trigger text"
                    }
                ]
            }
        """
        rubric = self.load_rubric(brand)
        rules = rubric.get("rules", [])
        reasons: List[Dict[str, Any]] = []

        content_lower = content.lower()

        # Step 1: Heuristic / Deterministic Rule Check
        for rule in rules:
            rule_id = rule.get("id")
            category = rule.get("category", "General Regulatory")
            fail_msg = rule.get("fail_message", f"Content violated compliance rule {rule_id}.")

            # Check trigger patterns (prohibited terms)
            patterns = rule.get("trigger_patterns", [])
            for pattern in patterns:
                pattern_clean = pattern.strip().lower()
                # Check for whole phrase match
                if pattern_clean in content_lower:
                    reasons.append({
                        "rule": rule_id,
                        "category": category,
                        "message": fail_msg,
                        "matched_phrase": pattern,
                    })
                    break

            # Check mandatory qualified phrases (if content makes coverage claims)
            required_phrases = rule.get("required_phrases", [])
            if required_phrases:
                # If content mentions coverage or claims or protection, it must include at least one qualifier
                coverage_keywords = ["cover", "policy", "benefit", "claim", "protection", "indemnity", "compensate"]
                has_coverage_keyword = any(kw in content_lower for kw in coverage_keywords)
                has_qualifier = any(req.lower() in content_lower for req in required_phrases)

                if has_coverage_keyword and not has_qualifier:
                    # Only add if not already flagged for absolute protection
                    already_flagged = any(r["rule"] in ("NO_GUARANTEED_PROTECTION", "NO_GUARANTEED_PAYOUT") for r in reasons)
                    if not already_flagged:
                        reasons.append({
                            "rule": rule_id,
                            "category": category,
                            "message": fail_msg,
                            "matched_phrase": "Missing regulatory qualifier",
                        })

        # Step 2: If live Gemini API is available and deterministic checks passed, run semantic LLM verification
        if gemini_service.is_live and len(reasons) == 0:
            llm_reasons = self._llm_check(content, brand, rules)
            reasons.extend(llm_reasons)

        # De-duplicate reasons by rule ID
        unique_reasons = []
        seen_rules = set()
        for r in reasons:
            if r["rule"] not in seen_rules:
                seen_rules.add(r["rule"])
                unique_reasons.append(r)

        status = "fail" if len(unique_reasons) > 0 else "pass"
        return {
            "status": status,
            "reasons": unique_reasons,
        }

    def _llm_check(self, content: str, brand: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optional secondary LLM semantic verification against regulatory rubrics."""
        rules_summary = "\n".join([
            f"- {r.get('id')}: {r.get('description')}" for r in rules
        ])

        system_instruction = (
            f"You are the Chief Regulatory Compliance Officer for InsurTech brand '{brand}'. "
            "Evaluate marketing content against strict advertising codes (MAS guidelines / MMC medical regulations). "
            "You must return ONLY a JSON object with this schema:\n"
            "{\"status\": \"pass\"|\"fail\", \"reasons\": [{\"rule\": \"RULE_ID\", \"category\": \"Category\", \"message\": \"Explanation\"}]}\n"
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
                    return parsed["reasons"]
        except Exception as exc:
            logger.debug(f"LLM compliance audit skipped or non-JSON: {exc}")

        return []


# Global agent instance
compliance_agent = ComplianceAgent()
