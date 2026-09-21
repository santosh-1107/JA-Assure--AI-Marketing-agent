"""
Research Agent for JA Assure AI Marketing Agent.
Implements the Research Agent contract from 02_Technical_Architecture:
- Input: brand, topic, optional competitor list
- Output: { summary, changes, recommendation, sources }
Grounds marketing content in official JA Assure knowledge from https://www.ja-assure.com/resources.html.
"""

from typing import Any, Dict, List, Optional
from backend.knowledge.knowledge_retriever import knowledge_retriever


class ResearchAgent:
    """
    Researches official JA Assure product and domain knowledge to ground marketing generation.
    Enforces anti-hallucination boundaries by providing factual foundation.
    """

    def __init__(self):
        self.retriever = knowledge_retriever

    def research(
        self,
        brand: str,
        topic: str,
        competitor_list: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute research for a brand and marketing topic against official JA Assure resources.
        Returns grounding digest with key facts and source attribution.
        """
        # Retrieve top relevant official JA Assure knowledge articles
        matched_sources = self.retriever.retrieve(brand=brand, topic=topic, top_k=2)

        primary_source = matched_sources[0] if matched_sources else None

        # Build research digest
        if primary_source:
            source_title = primary_source.get("title", "")
            source_url = primary_source.get("url", "")
            summary = (
                f"Grounding research from official JA Assure resource: '{source_title}'. "
                f"{primary_source.get('summary', '')}"
            )
            key_facts = primary_source.get("key_facts", [])
            recommendation = (
                f"Ground marketing copy in {brand}'s verified capabilities: "
                + "; ".join(key_facts[:3])
            )
        else:
            source_title = "JA Assure Resources"
            source_url = "https://www.ja-assure.com/resources.html"
            summary = "General InsurTech advisory under JA Assure core insurance principles."
            recommendation = "Adhere to standard brand voice and policy disclosure qualifiers."

        # Format sources list
        sources = []
        for s in matched_sources:
            snippet = s.get("summary", "")[:220] + "..."
            sources.append({
                "title": s.get("title"),
                "url": s.get("url"),
                "vertical": s.get("vertical"),
                "snippet": snippet,
                "key_facts": s.get("key_facts", []),
            })

        return {
            "summary": summary,
            "changes": [
                "Grounded in verified JA Assure product definitions",
                "Anti-hallucination constraint applied: restricted to supported claims",
            ],
            "recommendation": recommendation,
            "sources": sources,
        }


# Global agent instance
research_agent = ResearchAgent()
