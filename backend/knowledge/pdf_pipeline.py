"""
PDF Knowledge Ingestion Pipeline for JA Assure AI Marketing Intelligence Agent.
Extracts page-aware chunks and metadata from official JA Assure PDF documents.
Preserves document_id, filename, page_number, section, product, brand, source, text, document_type.
"""

import os
import re
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pypdf

logger = logging.getLogger(__name__)

PDF_DIR_DEFAULT = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge" / "pdfs"


def detect_brand_and_product(filename: str, page_text: str) -> Dict[str, str]:
    """Detect brand, product, and document_type from filename and content."""
    lower_name = filename.lower()
    lower_text = page_text.lower()

    if "jeweller" in lower_name or "jade" in lower_name or "jeweller" in lower_text:
        return {
            "brand": "Jade",
            "product": "Jewellers Block & Specie",
            "document_type": "product_guide",
            "source": "official JA Assure PDF",
        }
    elif "doctorshield" in lower_name or "medical" in lower_name or "malpractice" in lower_text or "indemnity" in lower_text:
        return {
            "brand": "DoctorShield",
            "product": "Medical Malpractice Indemnity",
            "document_type": "product_guide",
            "source": "official JA Assure PDF",
        }
    elif "architecture" in lower_name or "corporate" in lower_name or "ecosystem" in lower_text:
        return {
            "brand": "JA Assure",
            "product": "Insurance Architecture & Risk Pooling",
            "document_type": "corporate_foundation",
            "source": "official JA Assure PDF",
        }
    else:
        return {
            "brand": "JA Assure",
            "product": "Specialty InsurTech",
            "document_type": "general_knowledge",
            "source": "official JA Assure PDF",
        }


def extract_section_title(text: str) -> str:
    """Extract section heading from the first non-empty lines of text."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:3]:
        # Headings often contain hyphens, colon, or capitalized keywords
        if any(h in line.lower() for h in ["guideline", "overview", "warrant", "transit", "exclusion", "governance", "claim", "architecture", "ecosystem"]):
            return line[:80]
    return lines[0][:80] if lines else "General Provisions"


class PDFKnowledgePipeline:
    """
    Ingestion pipeline for official JA Assure PDF documents.
    Extracts text page-by-page, generates cohesive chunks, and tags each with rich metadata.
    """

    def __init__(self, pdf_dir: Optional[Path] = None):
        self.pdf_dir = Path(pdf_dir) if pdf_dir else PDF_DIR_DEFAULT
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def extract_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract page-aware chunks from a single PDF document.
        Preserves exact 1-indexed page_number and rich metadata per chunk.
        """
        if not file_path.exists() or file_path.suffix.lower() != ".pdf":
            raise FileNotFoundError(f"PDF file not found or invalid: {file_path}")

        filename = file_path.name
        doc_id = f"doc-{hashlib.md5(filename.encode('utf-8')).hexdigest()[:8]}"
        chunks: List[Dict[str, Any]] = []

        try:
            reader = pypdf.PdfReader(str(file_path))
            total_pages = len(reader.pages)

            for page_idx, page in enumerate(reader.pages):
                page_number = page_idx + 1  # 1-indexed
                raw_text = page.extract_text() or ""
                clean_text = raw_text.strip()
                if not clean_text:
                    continue

                classification = detect_brand_and_product(filename, clean_text)
                section = extract_section_title(clean_text)

                # Page-level chunking
                # If page is very long (> 1200 chars), split into 2 paragraph blocks
                paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
                if len(clean_text) > 1200 and len(paragraphs) > 1:
                    mid = len(paragraphs) // 2
                    part1_text = "\n\n".join(paragraphs[:mid])
                    part2_text = "\n\n".join(paragraphs[mid:])

                    chunks.append({
                        "chunk_id": f"{doc_id}-p{page_number}-c1",
                        "document_id": doc_id,
                        "filename": filename,
                        "page_number": page_number,
                        "section": f"{section} (Part 1)",
                        "product": classification["product"],
                        "brand": classification["brand"],
                        "document_type": classification["document_type"],
                        "source": classification["source"],
                        "text": part1_text,
                    })
                    chunks.append({
                        "chunk_id": f"{doc_id}-p{page_number}-c2",
                        "document_id": doc_id,
                        "filename": filename,
                        "page_number": page_number,
                        "section": f"{section} (Part 2)",
                        "product": classification["product"],
                        "brand": classification["brand"],
                        "document_type": classification["document_type"],
                        "source": classification["source"],
                        "text": part2_text,
                    })
                else:
                    chunks.append({
                        "chunk_id": f"{doc_id}-p{page_number}-c1",
                        "document_id": doc_id,
                        "filename": filename,
                        "page_number": page_number,
                        "section": section,
                        "product": classification["product"],
                        "brand": classification["brand"],
                        "document_type": classification["document_type"],
                        "source": classification["source"],
                        "text": clean_text,
                    })

            logger.info(f"Extracted {len(chunks)} chunks across {total_pages} pages from '{filename}'")
            return chunks

        except Exception as e:
            logger.error(f"Failed to extract text from PDF '{filename}': {e}")
            raise

    def ingest_all_pdfs(self) -> List[Dict[str, Any]]:
        """
        Process all PDF files found in self.pdf_dir.
        Returns a list of all extracted chunk dictionaries.
        """
        pdf_files = sorted(list(self.pdf_dir.glob("*.pdf")))
        all_chunks: List[Dict[str, Any]] = []

        for pdf_file in pdf_files:
            chunks = self.extract_document(pdf_file)
            all_chunks.extend(chunks)

        return all_chunks

    def list_available_pdfs(self) -> List[Dict[str, Any]]:
        """List all PDFs currently in the storage folder with metadata."""
        pdf_files = sorted(list(self.pdf_dir.glob("*.pdf")))
        results = []
        for p in pdf_files:
            try:
                reader = pypdf.PdfReader(str(p))
                page_count = len(reader.pages)
            except Exception:
                page_count = 0

            preview_info = detect_brand_and_product(p.name, "")
            results.append({
                "filename": p.name,
                "file_path": str(p),
                "size_bytes": p.stat().st_size,
                "page_count": page_count,
                "brand": preview_info["brand"],
                "product": preview_info["product"],
                "document_type": preview_info["document_type"],
            })
        return results


# Global pipeline instance
pdf_pipeline = PDFKnowledgePipeline()
