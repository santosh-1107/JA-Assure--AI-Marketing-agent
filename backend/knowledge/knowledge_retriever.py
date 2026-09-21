"""
Lightweight Knowledge Retriever for JA Assure AI Marketing Agent.
Matches topics and brands against verified JA Assure resources from https://www.ja-assure.com/resources.html.
Provides factual grounding context to eliminate hallucination without heavy vector database overhead.
"""

from typing import Any, Dict, List, Optional
from backend.knowledge.ja_assure_sources import load_all_sources


class KnowledgeRetriever:
    """
    Retrieves relevant official JA Assure knowledge for a given brand and topic.
    Uses brand affiliation and keyword relevance scoring.
    """

    def __init__(self):
        self.sources = load_all_sources()

    def retrieve(
        self,
        brand: str,
        topic: str,
        top_k: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top matching JA Assure knowledge articles for the given brand and topic.
        Returns a list of source objects with relevance scores and key grounding facts.
        """
        scored_sources = []
        topic_lower = topic.lower()
        topic_tokens = set(topic_lower.replace(",", " ").replace(".", " ").split())
        normalized_brand = "jade" if "jade" in brand.lower() else ("doctorshield" if "doctor" in brand.lower() else "")

        for source in self.sources:
            score = 0.0
            src_brand = source.get("brand", "").lower()

            # Brand affinity bonus
            if normalized_brand and src_brand == normalized_brand:
                score += 5.0
            elif src_brand == "general":
                score += 1.0

            # Keyword matching in title
            title_lower = source.get("title", "").lower()
            for token in topic_tokens:
                if len(token) > 2 and token in title_lower:
                    score += 3.0

            # Keyword matching against source tags
            for kw in source.get("keywords", []):
                kw_lower = kw.lower()
                if kw_lower in topic_lower or any(token in kw_lower for token in topic_tokens if len(token) > 3):
                    score += 2.0

            # Keyword matching in summary
            summary_lower = source.get("summary", "").lower()
            for token in topic_tokens:
                if len(token) > 3 and token in summary_lower:
                    score += 0.5

            if score > 0:
                scored_sources.append((score, source))

        # Sort by relevance descending
        scored_sources.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, src in scored_sources[:top_k]:
            results.append({
                "id": src.get("id"),
                "title": src.get("title"),
                "url": src.get("url"),
                "brand": src.get("brand"),
                "vertical": src.get("vertical"),
                "summary": src.get("summary"),
                "key_facts": src.get("key_facts", []),
                "relevance_score": score,
            })

        # Fallback if no specific match
        if not results:
            fallback = self._get_default_source(brand)
            results.append({
                "id": fallback.get("id"),
                "title": fallback.get("title"),
                "url": fallback.get("url"),
                "brand": fallback.get("brand"),
                "vertical": fallback.get("vertical"),
                "summary": fallback.get("summary"),
                "key_facts": fallback.get("key_facts", []),
                "relevance_score": 1.0,
            })

        return results

    def _get_default_source(self, brand: str) -> Dict[str, Any]:
        """Provide primary brand grounding when topic is generic."""
        if "jade" in brand.lower():
            for s in self.sources:
                if s.get("id") == "jewellers_block":
                    return s
        else:
            for s in self.sources:
                if s.get("id") == "medical_indemnity":
                    return s
        return self.sources[0]


# Global retriever instance
knowledge_retriever = KnowledgeRetriever()
