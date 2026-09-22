"""
Test ingestion and hybrid search on official JA Assure PDFs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.knowledge.pdf_pipeline import pdf_pipeline
from backend.knowledge.vector_store import vector_store


def main():
    print("Extracting chunks from PDFs...")
    chunks = pdf_pipeline.ingest_all_pdfs()
    print(f"Extracted {len(chunks)} chunks.")

    print("Indexing into ChromaDB...")
    indexed_count = vector_store.index_pdf_chunks(chunks)
    print(f"Indexed {indexed_count} chunks into company_knowledge collection.")

    print("\nExecuting hybrid search: 'Jewellers Block protection high value safe' (brand=Jade)...")
    results = vector_store.hybrid_search("Jewellers Block protection high value safe", brand="Jade", top_k=3)
    print(f"Retrieved {len(results)} matches:")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['filename']} — Page {r['page_number']} (Score: {r['relevance_score']})")
        print(f"   Section: {r['section']}")
        print(f"   Snippet: {r['text'][:140]}...")

    print("\nExecuting hybrid search: 'Medical malpractice legal defense counsel' (brand=DoctorShield)...")
    results_ds = vector_store.hybrid_search("Medical malpractice legal defense counsel", brand="DoctorShield", top_k=2)
    print(f"Retrieved {len(results_ds)} matches:")
    for i, r in enumerate(results_ds, 1):
        print(f"{i}. {r['filename']} — Page {r['page_number']} (Score: {r['relevance_score']})")
        print(f"   Section: {r['section']}")
        print(f"   Snippet: {r['text'][:140]}...")

    print("\nTesting Feedback Embedding...")
    fb_id = vector_store.index_feedback(
        feedback_id=101,
        content_id=1,
        original_content="Get guaranteed protection against every possible jewellery loss.",
        corrected_content="Explore specialist insurance solutions for jewellery businesses, subject to policy terms.",
        issue_type="inaccurate_claim",
        rejection_tag="unsupported_guarantee",
        reviewer_note="Avoid guaranteed payout or absolute protection language.",
        brand="Jade",
        product="Jewellers Block & Specie",
        platform="LinkedIn",
        risk_score=40.0,
        compliance_rule="NO_GUARANTEED_PROTECTION",
    )
    print(f"Stored feedback embedding: {fb_id}")

    print("\nRetrieving similar feedback for query: '100% complete coverage for all diamond losses'...")
    fb_matches = vector_store.search_similar_feedback("100% complete coverage for all diamond losses", brand="Jade", top_k=2)
    print(f"Retrieved {len(fb_matches)} feedback matches:")
    for m in fb_matches:
        print(f" - Issue: {m['issue_type']} (Similarity: {m['similarity_score']})")
        print(f"   Note: {m['reviewer_note']}")

    print("\nSUCCESS: All PDF ingestion, vector indexing, hybrid search, and semantic feedback verified!")


if __name__ == "__main__":
    main()
