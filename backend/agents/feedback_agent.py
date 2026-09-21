"""
Feedback Agent for JA Assure AI Marketing Agent.
Retrieves historical human review feedback, compiles few-shot prompt injections,
and computes rejection rate analytics across review cycles.
"""

from typing import Any, Dict, List, Optional
from backend.models import get_recent_feedback as db_get_recent_feedback
from backend.models import get_rejection_rate_by_cycle as db_get_rejection_rate


class FeedbackAgent:
    """
    Manages the learning loop: pulls reviewer feedback from SQLite,
    formats it as actionable few-shot constraints for the Content Agent,
    and analyzes review trend metrics.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def get_recent_feedback(self, brand: str, n: int = 5) -> List[Dict[str, Any]]:
        """Fetch the last N human feedback items for the specified brand."""
        return db_get_recent_feedback(brand=brand, n=n, db_path=self.db_path)

    def format_feedback_for_prompt(self, feedback_items: List[Dict[str, Any]]) -> str:
        """
        Format recent reviewer notes into structured prompt instructions.
        Ensures the Content Agent explicitly avoids past mistakes.
        """
        if not feedback_items:
            return "No previous human corrections on record. Adhere to standard brand voice."

        lines = [
            "=== CRITICAL LESSONS LEARNED FROM PREVIOUS HUMAN REVIEWS ===",
            "Human compliance reviewers previously REJECTED marketing assets for this brand due to the following errors.",
            "You MUST explicitly learn from these corrections and NOT repeat them:",
        ]

        for i, item in enumerate(feedback_items, 1):
            tag = item.get("tag", "regulatory_feedback")
            note = item.get("note", "")
            lines.append(f"{i}. [{tag.upper()}]: {note}")

        lines.append(
            "\nRequirement: Verify that your generated output directly avoids every issue listed above."
        )
        return "\n".join(lines)

    def get_rejection_rate_analytics(self) -> Dict[str, Any]:
        """
        Compute rejection rate trends across review cycles.
        Returns detailed cycle breakdown and overall statistics.
        """
        cycle_stats = db_get_rejection_rate(db_path=self.db_path)
        total_reviewed = sum(item["total"] for item in cycle_stats)
        total_rejected = sum(item["rejected"] for item in cycle_stats)
        overall_rate = round((total_rejected / total_reviewed * 100), 1) if total_reviewed > 0 else 0.0

        return {
            "cycles": cycle_stats,
            "total_reviewed": total_reviewed,
            "total_rejected": total_rejected,
            "overall_rejection_rate": overall_rate,
        }


# Global agent instance
feedback_agent = FeedbackAgent()
