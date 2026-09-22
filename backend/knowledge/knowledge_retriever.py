"""
Hybrid Knowledge Retriever for JA Assure AI Marketing Intelligence & Risk Agent.
Queries official JA Assure PDF documents from data/knowledge/pdfs/ via ChromaDB vector store.
Retains exact document_id, filename, page_number, section, and relevance score for source citations.
Falls back to verified JA Assure resource JSONs when PDF index is initializing.
"""

import logging
from typing import Any, Dict, List, Optional
from backend.knowledge.ja_assure_sources import load_all_sources
from backend.knowledge.vector_store import vector_store
from backend.knowledge.pdf_pipeline import pdf_pipeline

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Retrieves Tier 1 Authoritative Company Knowledge for a given brand and marketing topic.
    Blends ChromaDB vector similarity with keyword/BM25 token ranking.
    Preserves page_number, filename, and section for user-facing source citations.
    """

    def __init__(self):
        self.sources = load_all_sources()
        self.vector_store = vector_store
        self.pdf_pipeline = pdf_pipeline
        self._ensure_pdf_index()

    def _ensure_pdf_index(self):
        """Ensure seed PDFs are indexed in ChromaDB on initialization."""
        try:
            if self.vector_store.company_collection.count() == 0:
                chunks = self.pdf_pipeline.ingest_all_pdfs()
                if chunks:
                    self.vector_store.index_pdf_chunks(chunks)
                    logger.info(f"Auto-indexed {len(chunks)} PDF chunks into ChromaDB.")
        except Exception as e:
            logger.warning(f"Auto-indexing PDFs encountered notice: {e}")

    def retrieve(
        self,
        brand: str,
        topic: str,
        product: Optional[str] = None,
        top_k: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top matching official JA Assure knowledge chunks.
        Returns a list of source objects with filename, page_number, section, and relevance scores.
        """
        results: List[Dict[str, Any]] = []

        # 1. Attempt hybrid vector search against authoritative PDF knowledge
        try:
            pdf_matches = self.vector_store.hybrid_search(
                query=topic,
                brand=brand,
                product=product,
                top_k=top_k,
            )
            for m in pdf_matches:
                # Extract clean bullet points / key facts from text
                text_lines = [l.strip("•- \t") for l in m["text"].split("\n") if len(l.strip("•- \t")) > 20]
                chunk_facts = text_lines[:3] if text_lines else [m["text"][:120]]

                # Map to canonical JA Assure resource metadata for contract compatibility
                canonical = self._get_canonical_resource(brand=m.get("brand", brand), filename=m.get("filename", ""))
                combined_facts = list(canonical.get("key_facts", []))
                for f in chunk_facts:
                    if f not in combined_facts:
                        combined_facts.append(f)

                results.append({
                    "id": canonical.get("id", m["chunk_id"]),
                    "chunk_id": m["chunk_id"],
                    "title": canonical.get("title", f"{m.get('product', brand)} ({m['filename']}, Page {m['page_number']})"),
                    "filename": m["filename"],
                    "page_number": m["page_number"],
                    "section": m["section"],
                    "product": m["product"],
                    "brand": m["brand"],
                    "source_type": "official_ja_assure",
                    "source": f"Official JA Assure PDF ({m['filename']})",
                    "url": canonical.get("url", f"https://www.ja-assure.com/resources.html#page={m['page_number']}"),
                    "vertical": canonical.get("vertical", m.get("product", brand)),
                    "summary": m["text"][:260] + "..." if len(m["text"]) > 260 else m["text"],
                    "key_facts": combined_facts,
                    "relevance_score": m["relevance_score"],
                    "text": m["text"],
                    "tier": "TIER_1_AUTHORITATIVE",
                })
        except Exception as e:
            logger.warning(f"Hybrid vector search failed, falling back to static resources: {e}")

        # 2. Fallback to structured JA Assure resource JSONs if no PDF matches found
        if not results:
            results = self._retrieve_static_fallback(brand=brand, topic=topic, top_k=top_k)

        # 3. If topic has zero domain relevance to JA Assure, do not return unrelated knowledge
        insurance_domain_terms = {
            "jewell", "specie", "gold", "diamond", "gem", "vault", "watch", "transit",
            "cargo", "courier", "logistics", "shipping", "transport", "freight",
            "medic", "doctor", "clinic", "hospital", "malpractice", "indemnity", "patient",
            "surgeon", "physician", "liability", "insurance", "underwriting", "risk", "coverage",
            "policy", "claim", "governance", "advisory", "precious", "uncertainty", "ecosystem",
            "protect", "financial", "wealth", "asset", "safeguard", "heirloom", "luxury", "private", "commercial"
        }
        topic_lower = (topic or "").lower()
        has_domain_overlap = any(term in topic_lower for term in insurance_domain_terms)
        if not has_domain_overlap and not any(r.get("relevance_score", 0) > 2.0 for r in results):
            return []

        return results

    def _retrieve_static_fallback(self, brand: str, topic: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Fallback static keyword matching if PDF index is unavailable."""
        scored_sources = []
        topic_lower = topic.lower()
        topic_tokens = set(topic_lower.replace(",", " ").replace(".", " ").split())
        normalized_brand = "jade" if "jade" in brand.lower() else ("doctorshield" if "doctor" in brand.lower() else "")

        for source in self.sources:
            score = 0.0
            src_brand = source.get("brand", "").lower()

            if normalized_brand and src_brand == normalized_brand:
                score += 3.0
            elif src_brand == "general":
                score += 1.0

            title_lower = source.get("title", "").lower()
            summary_lower = source.get("summary", "").lower()
            overlap = 0

            for token in topic_tokens:
                if len(token) > 2:
                    if token in title_lower:
                        score += 3.0
                        overlap += 1
                    elif token in summary_lower:
                        score += 1.5
                        overlap += 1

            for kw in source.get("keywords", []):
                kw_lower = kw.lower()
                if kw_lower in topic_lower or any(token in kw_lower for token in topic_tokens if len(token) > 3):
                    score += 2.0
                    overlap += 1

            if overlap > 0:
                scored_sources.append((score, source))

        scored_sources.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, src in scored_sources[:top_k]:
            results.append({
                "id": src.get("id"),
                "title": src.get("title"),
                "filename": f"{src.get('id')}.pdf",
                "page_number": 1,
                "section": "Overview",
                "product": src.get("title"),
                "brand": src.get("brand"),
                "source_type": "official_ja_assure",
                "url": src.get("url"),
                "vertical": src.get("vertical"),
                "summary": src.get("summary"),
                "key_facts": src.get("key_facts", []),
                "relevance_score": score,
                "text": src.get("summary", ""),
            })

        if not results:
            # Only provide brand default if topic is generic/brand-relevant, not unrelated
            insurance_domain_terms = {
                "jewell", "specie", "gold", "diamond", "gem", "vault", "watch", "transit",
                "cargo", "courier", "logistics", "shipping", "transport", "freight",
                "medic", "doctor", "clinic", "hospital", "malpractice", "indemnity", "patient",
                "surgeon", "physician", "liability", "insurance", "underwriting", "risk", "coverage",
                "policy", "claim", "governance", "advisory", "precious"
            }
            if any(t in topic_lower for t in insurance_domain_terms) or not topic_lower.strip():
                fallback = self._get_default_source(brand)
                results.append({
                    "id": fallback.get("id"),
                    "title": fallback.get("title"),
                    "filename": f"{fallback.get('id')}.pdf",
                    "page_number": 1,
                    "section": "Core Guidelines",
                    "product": fallback.get("title"),
                    "brand": fallback.get("brand"),
                    "source_type": "official_ja_assure",
                    "url": fallback.get("url"),
                    "vertical": fallback.get("vertical"),
                    "summary": fallback.get("summary"),
                    "key_facts": fallback.get("key_facts", []),
                    "relevance_score": 1.0,
                    "text": fallback.get("summary", ""),
                })

        return results

    def _get_canonical_resource(self, brand: str, filename: str = "") -> Dict[str, Any]:
        """Find canonical official JA Assure resource matching brand or filename."""
        fn_lower = filename.lower()
        if "jewell" in fn_lower or "specie" in fn_lower:
            for s in self.sources:
                if s.get("id") == "jewellers_block":
                    return s
        elif "doctor" in fn_lower or "med" in fn_lower or "malpractice" in fn_lower:
            for s in self.sources:
                if s.get("id") == "medical_indemnity":
                    return s
        elif "corporate" in fn_lower or "architecture" in fn_lower:
            for s in self.sources:
                if s.get("id") in ("architecture_uncertainty", "architecture_of_uncertainty"):
                    return s
        elif "ecosystem" in fn_lower:
            for s in self.sources:
                if s.get("id") == "insurance_ecosystem":
                    return s

        return self._get_default_source(brand)

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
