"""
Vector Store Management for JA Assure AI Marketing Intelligence Agent.
Implements local persistent ChromaDB with two strictly isolated collections:
  1. 'company_knowledge' — Authoritative JA Assure PDF chunks (Tier 1).
  2. 'feedback_embeddings' — Historical human reviewer edits and rejections (Reviewer corrections).
Provides hybrid retrieval (vector similarity + keyword filtering) and source attribution with exact page citations.
"""

import os
import re
import math
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger(__name__)

CHROMA_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chromadb"


class FastLocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    High-performance, local deterministic semantic embedding function.
    Eliminates external 80MB ONNX download delays and network failures.
    Generates L2-normalized dense semantic vectors (dim=256) combining word tokens,
    sub-word character n-grams (3-grams, 4-grams), and domain semantic clusters.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = [w for w in clean.split() if len(w) > 1]
        if not words:
            return [1.0 / math.sqrt(self.dim)] * self.dim

        # 1. Word-level features
        for w in words:
            # Domain-weighted terms
            weight = 2.5 if w in (
                "jeweller", "jewellery", "diamond", "specie", "malpractice", "indemnity",
                "guarantee", "guaranteed", "payout", "vault", "transit", "safe", "theft",
                "coverage", "underwriting", "negligence", "medical", "jade", "doctorshield",
                "unsupported", "salesy", "tone", "exclusion", "counsel", "claim"
            ) else 1.0

            h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.dim
            vec[idx] += weight

            # 2. Sub-word character n-grams (3-grams, 4-grams) for semantic & morphological capture
            for n in (3, 4):
                if len(w) >= n:
                    for i in range(len(w) - n + 1):
                        ngram = w[i:i+n]
                        nh = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:6], 16)
                        nidx = nh % self.dim
                        vec[nidx] += 0.35 * weight

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return [1.0 / math.sqrt(self.dim)] * self.dim

    def name(self) -> str:
        return "fast_local"

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_text(doc) for doc in input]


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for keyword BM25-style scoring."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in clean.split() if len(t) > 2]


class VectorStoreManager:
    """
    Manages local ChromaDB vector store.
    Enforces absolute isolation between company knowledge and feedback embeddings.
    """

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = Path(persist_dir) if persist_dir else CHROMA_DATA_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_fn = FastLocalEmbeddingFunction()

        # Isolated Collections with local embedding function
        try:
            self.company_collection = self.client.get_or_create_collection(
                name="company_knowledge",
                embedding_function=self.embedding_fn,
                metadata={"description": "Authoritative JA Assure official PDF chunks (Tier 1)"},
            )
        except Exception:
            try:
                self.client.delete_collection("company_knowledge")
            except Exception:
                pass
            self.company_collection = self.client.create_collection(
                name="company_knowledge",
                embedding_function=self.embedding_fn,
                metadata={"description": "Authoritative JA Assure official PDF chunks (Tier 1)"},
            )

        try:
            self.feedback_collection = self.client.get_or_create_collection(
                name="feedback_embeddings",
                embedding_function=self.embedding_fn,
                metadata={"description": "Human reviewer rejections and edits for semantic learning"},
            )
        except Exception:
            try:
                self.client.delete_collection("feedback_embeddings")
            except Exception:
                pass
            self.feedback_collection = self.client.create_collection(
                name="feedback_embeddings",
                embedding_function=self.embedding_fn,
                metadata={"description": "Human reviewer rejections and edits for semantic learning"},
            )

    # =========================================================================
    # Tier 1: Company Knowledge Ingestion & Retrieval
    # =========================================================================

    def index_pdf_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Index extracted PDF chunks into 'company_knowledge'.
        Preserves all required metadata:
          document_id, filename, page_number, section, product, brand, source, text, document_type.
        """
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for c in chunks:
            chunk_id = c.get("chunk_id") or f"{c['document_id']}-p{c['page_number']}"
            ids.append(chunk_id)
            documents.append(c["text"])
            metadatas.append({
                "document_id": str(c.get("document_id", "")),
                "filename": str(c.get("filename", "")),
                "page_number": int(c.get("page_number", 1)),
                "section": str(c.get("section", "General")),
                "product": str(c.get("product", "Specialty")),
                "brand": str(c.get("brand", "JA Assure")),
                "source": str(c.get("source", "official JA Assure PDF")),
                "document_type": str(c.get("document_type", "product")),
            })

        # Upsert into ChromaDB
        self.company_collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Indexed {len(ids)} PDF chunks into company_knowledge collection.")
        return len(ids)

    def hybrid_search(
        self,
        query: str,
        brand: Optional[str] = None,
        product: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining vector similarity search and keyword/BM25 token filtering.
        Returns ranked passages preserving exact filename, page_number, section, and relevance score.
        """
        if not query or not query.strip():
            return []

        # 1. Vector similarity search from ChromaDB
        where_filter = None
        if brand and brand.lower() in ("jade", "doctorshield"):
            target_brand = "Jade" if brand.lower() == "jade" else "DoctorShield"
            # Allow brand-specific documents or corporate general documents
            where_filter = {"brand": {"$in": [target_brand, "JA Assure"]}}

        count = self.company_collection.count()
        if count == 0:
            return []

        n_results = min(top_k * 2, count)

        try:
            query_kwargs: Dict[str, Any] = {
                "query_texts": [query],
                "n_results": n_results,
            }
            if where_filter:
                query_kwargs["where"] = where_filter

            res = self.company_collection.query(**query_kwargs)
        except Exception as e:
            logger.warning(f"Vector query with filter failed, falling back to unconstrained query: {e}")
            res = self.company_collection.query(
                query_texts=[query],
                n_results=n_results,
            )

        # 2. Combine vector distance with keyword/brand boost
        query_tokens = set(tokenize(query))
        scored_candidates = []

        ids = res["ids"][0] if res and res.get("ids") else []
        documents = res["documents"][0] if res and res.get("documents") else []
        metadatas = res["metadatas"][0] if res and res.get("metadatas") else []
        distances = res["distances"][0] if res and res.get("distances") else [0.5] * len(ids)

        for i, doc_id in enumerate(ids):
            doc_text = documents[i]
            meta = metadatas[i]
            dist = distances[i] if i < len(distances) else 1.0

            # Vector similarity score (1 / (1 + distance))
            vec_sim = 1.0 / (1.0 + max(0.0, float(dist)))

            # Keyword matching score
            doc_tokens = set(tokenize(doc_text))
            keyword_overlap = len(query_tokens.intersection(doc_tokens))
            kw_score = min(keyword_overlap * 0.1, 0.4)

            # Brand alignment boost
            brand_boost = 0.0
            if brand:
                doc_brand = meta.get("brand", "").lower()
                if brand.lower() in doc_brand:
                    brand_boost = 0.15

            combined_score = round(vec_sim * 0.65 + kw_score + brand_boost, 3)

            scored_candidates.append({
                "chunk_id": doc_id,
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "page_number": int(meta.get("page_number", 1)),
                "section": meta.get("section", "General"),
                "product": meta.get("product"),
                "brand": meta.get("brand"),
                "source": meta.get("source", "official JA Assure PDF"),
                "source_type": "official_pdf",
                "text": doc_text,
                "relevance_score": combined_score,
            })

        # Sort descending by combined score
        scored_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_candidates[:top_k]

    def get_company_knowledge_stats(self) -> Dict[str, Any]:
        """Return collection summary for Knowledge Library display."""
        total_chunks = self.company_collection.count()
        # Peek to gather document names and products
        peek = self.company_collection.peek(limit=50)
        docs_summary: Dict[str, Dict[str, Any]] = {}

        if peek and peek.get("metadatas"):
            for m in peek["metadatas"]:
                fn = m.get("filename", "unknown")
                if fn not in docs_summary:
                    docs_summary[fn] = {
                        "filename": fn,
                        "product": m.get("product", ""),
                        "brand": m.get("brand", ""),
                        "document_type": m.get("document_type", ""),
                        "pages": set(),
                        "chunks_count": 0,
                    }
                docs_summary[fn]["pages"].add(m.get("page_number", 1))
                docs_summary[fn]["chunks_count"] += 1

        doc_list = []
        for fn, info in docs_summary.items():
            doc_list.append({
                "filename": fn,
                "product": info["product"],
                "brand": info["brand"],
                "document_type": info["document_type"],
                "total_pages": len(info["pages"]),
                "chunk_count": info["chunks_count"],
                "status": "indexed",
            })

        return {
            "total_chunks": total_chunks,
            "indexed_documents": doc_list,
        }

    # =========================================================================
    # Tier 2: Semantic Feedback Learning & Retrieval
    # =========================================================================

    def index_feedback(
        self,
        feedback_id: Any,
        content_id: int = 0,
        original_content: str = "",
        corrected_content: Optional[str] = None,
        issue_type: str = "inaccurate_claim",
        rejection_tag: Optional[str] = None,
        reviewer_note: Optional[str] = None,
        brand: str = "JA Assure",
        product: Optional[str] = None,
        platform: Optional[str] = None,
        risk_score: Optional[float] = None,
        compliance_rule: Optional[str] = None,
        timestamp: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Create and store vector embedding for a reviewer rejection or correction.
        Vector text encodes the flawed claim, reviewer note, and correction.
        """
        tag_val = rejection_tag or kwargs.get("tag") or issue_type
        note_val = reviewer_note or kwargs.get("note") or ""
        flawed_val = original_content or kwargs.get("flawed_content") or ""

        embed_id = f"fb-{feedback_id}"

        # Build text representation for high-fidelity semantic similarity
        embed_text = (
            f"Brand: {brand} | Platform: {platform or 'General'} | Issue: {issue_type} ({tag_val})\n"
            f"Original Flawed Content: {flawed_val}\n"
            f"Reviewer Correction Note: {note_val}\n"
            f"Corrected Content: {corrected_content or 'Removed non-compliant phrasing.'}"
        )

        metadata = {
            "feedback_id": str(feedback_id),
            "content_id": int(content_id),
            "brand": str(brand),
            "product": str(product or "General"),
            "platform": str(platform or "General"),
            "issue_type": str(issue_type or tag_val),
            "rejection_tag": str(tag_val),
            "reviewer_note": str(note_val),
            "risk_score": float(risk_score or 0.0),
            "compliance_rule": str(compliance_rule or ""),
            "timestamp": str(timestamp or ""),
        }

        self.feedback_collection.upsert(
            ids=[embed_id],
            documents=[embed_text],
            metadatas=[metadata],
        )
        logger.info(f"Stored feedback embedding '{embed_id}' for brand '{brand}'.")
        return embed_id

    def search_similar_feedback(
        self,
        query: str,
        brand: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar historical corrections.
        Used before generation to identify relevant past mistakes.
        """
        count = self.feedback_collection.count()
        if count == 0:
            return []

        n_results = min(max(top_k * 4, 15), count)
        where_filter = {"brand": brand} if brand else None

        try:
            res = self.feedback_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
        except Exception as e:
            logger.warning(f"Feedback query with filter failed, falling back to unconstrained query: {e}")
            res = self.feedback_collection.query(
                query_texts=[query],
                n_results=n_results,
            )

        matches = []
        ids = res["ids"][0] if res and res.get("ids") else []
        metadatas = res["metadatas"][0] if res and res.get("metadatas") else []
        documents = res["documents"][0] if res and res.get("documents") else []
        distances = res["distances"][0] if res and res.get("distances") else [0.5] * len(ids)

        structural_stop_words = {
            "brand", "platform", "jade", "doctorshield", "linkedin", "instagram",
            "x", "post", "general", "issue", "product", "the", "a", "an", "and",
            "or", "for", "in", "to", "with", "of", "on", "at", "by", "from"
        }
        query_tokens = set(tokenize(query)) - structural_stop_words

        for i, fb_id in enumerate(ids):
            meta = metadatas[i]
            dist = distances[i] if i < len(distances) else 1.0
            similarity = 1.0 / (1.0 + max(0.0, float(dist)))

            # Keyword and domain token overlap on meaningful content terms
            doc_text = (documents[i] or "") + " " + (meta.get("reviewer_note") or "") + " " + (meta.get("rejection_tag") or "")
            doc_tokens = set(tokenize(doc_text)) - structural_stop_words
            overlap = len(query_tokens.intersection(doc_tokens))
            kw_score = min(overlap * 0.20, 0.50)

            combined_score = round(similarity * 0.50 + kw_score, 3)

            matches.append({
                "feedback_id": meta.get("feedback_id"),
                "content_id": meta.get("content_id"),
                "brand": meta.get("brand"),
                "platform": meta.get("platform"),
                "issue_type": meta.get("issue_type"),
                "rejection_tag": meta.get("rejection_tag"),
                "tag": meta.get("rejection_tag"),
                "reviewer_note": meta.get("reviewer_note"),
                "compliance_rule": meta.get("compliance_rule"),
                "risk_score": meta.get("risk_score"),
                "similarity_score": combined_score,
                "summary": documents[i],
            })

        # Sort by combined similarity descending
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches[:top_k]


# Global vector store manager instance
vector_store = VectorStoreManager()
