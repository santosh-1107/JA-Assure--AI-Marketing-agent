"""
Feedback Agent for JA Assure AI Marketing Intelligence Agent.
Retrieves historical human review feedback via semantic vector search (ChromaDB)
and structured database queries, compiling few-shot negative constraints for ContentAgent.
"""

from typing import Any, Dict, List, Optional
from backend.models import get_recent_feedback as db_get_recent_feedback
from backend.models import get_rejection_rate_by_cycle as db_get_rejection_rate
from backend.knowledge.vector_store import vector_store


class FeedbackAgent:
    """
    Manages semantic feedback learning:
    Queries ChromaDB feedback_embeddings collection for semantically relevant historical reviewer corrections.
    Formats negative few-shot constraints so ContentAgent actively avoids past mistakes.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.vector_store = vector_store

    def get_recent_feedback(self, brand: str, n: int = 5) -> List[Dict[str, Any]]:
        """Fetch the last N human feedback items for the specified brand from SQLite."""
        return db_get_recent_feedback(brand=brand, n=n, db_path=self.db_path)

    def retrieve_semantic_feedback(
        self,
        topic: str,
        brand: str,
        product: Optional[str] = None,
        platform: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Build semantic query from topic, brand, product, and platform.
        Retrieve most relevant historical corrections from feedback_embeddings collection.
        Falls back to database records if vector collection has few entries.
        """
        semantic_query = f"{brand} {product or ''} {platform or ''}: {topic}".strip()
        matches: List[Dict[str, Any]] = []

        try:
            vector_matches = self.vector_store.search_similar_feedback(
                query=semantic_query,
                brand=brand,
                top_k=top_k,
            )
            matches.extend(vector_matches)
        except Exception:
            pass

        # If vector store has fewer results than top_k, supplement with recent SQLite feedback
        if len(matches) < top_k:
            recent_db = self.get_recent_feedback(brand=brand, n=top_k)
            seen_fb_ids = {m.get("feedback_id") for m in matches if m.get("feedback_id")}
            for fb in recent_db:
                if fb["id"] not in seen_fb_ids:
                    matches.append({
                        "feedback_id": fb["id"],
                        "content_id": fb["content_id"],
                        "brand": fb["brand"],
                        "platform": fb.get("platform", platform),
                        "issue_type": fb.get("issue_type") or fb.get("tag", "general_feedback"),
                        "rejection_tag": fb.get("tag"),
                        "reviewer_note": fb.get("note", ""),
                        "compliance_rule": fb.get("compliance_rule", ""),
                        "risk_score": fb.get("risk_score", 0.0),
                        "similarity_score": 0.5,
                        "original_content": fb.get("original_content", ""),
                        "corrected_content": fb.get("corrected_content", ""),
                    })
                    seen_fb_ids.add(fb["id"])
                    if len(matches) >= top_k:
                        break

        return matches[:top_k]

    def format_feedback_for_prompt(self, feedback_items: List[Dict[str, Any]]) -> str:
        """
        Format retrieved reviewer notes into structured prompt instructions.
        Explicitly warns ContentAgent: 'Similar historical feedback exists. Avoid repeating this pattern.'
        """
        if not feedback_items:
            return "No previous human corrections on record for this topic. Adhere to standard brand voice."

        lines = [
            "=== CRITICAL LESSONS LEARNED FROM PREVIOUS HUMAN REVIEWS ===",
            "Similar historical feedback exists for this domain. You MUST avoid repeating these patterns:",
        ]

        for i, item in enumerate(feedback_items, 1):
            issue = item.get("issue_type") or item.get("tag") or item.get("rejection_tag") or "regulatory_flaw"
            note = item.get("reviewer_note") or item.get("note") or ""
            rule = item.get("compliance_rule")
            rule_str = f" [Rule: {rule}]" if rule else ""

            orig = item.get("original_content") or ""
            corr = item.get("corrected_content") or ""

            entry = f"{i}. Issue: [{issue.upper()}]{rule_str}\n   Reviewer Correction: \"{note}\""
            if orig:
                entry += f"\n   Past Flawed Phrasing: \"{orig[:120]}...\"" if len(orig) > 120 else f"\n   Past Flawed Phrasing: \"{orig}\""
            if corr:
                entry += f"\n   Approved Replacement: \"{corr[:120]}...\"" if len(corr) > 120 else f"\n   Approved Replacement: \"{corr}\""

            lines.append(entry)

        lines.append(
            "\nMandatory Directive: Under no circumstances repeat any of the rejected phrases or claims above."
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
