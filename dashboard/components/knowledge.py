"""
Knowledge Library Component for JA Assure.
Provides the official document library and the right-rail knowledge widget matching the reference design.
"""

import streamlit as st
from typing import Any, Dict, List
from backend.knowledge.ja_assure_sources import load_all_sources


def render_knowledge_right_widget():
    """
    Renders the right-rail 'JA Assure Knowledge' card matching the reference image:
    - 5 official resources with small thumbnail icons
    - 'Browse All Resources →' CTA button
    """
    sources = load_all_sources()

    st.markdown(
        """
        <div class="right-widget-card">
            <div class="widget-header">
                <span style="font-size: 1.1rem; color: #2563EB;">📖</span>
                <div>
                    <div class="widget-title">JA Assure Knowledge</div>
                    <div class="widget-sub">5 Official Resources</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for s in sources[:5]:
        st.markdown(
            f"""
            <div class="resource-list-item">
                <div class="resource-thumb">📄</div>
                <div style="flex: 1;">
                    <div class="resource-item-title">{s.get('title')}</div>
                    <div class="resource-item-sub">{s.get('summary', '')[:50]}... →</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("Browse All Resources →", key="btn_browse_resources", use_container_width=True):
        st.session_state["active_page"] = "Knowledge Library"
        st.rerun()


def render_knowledge_library_page():
    """
    Renders the upgraded JA Assure PDF Knowledge Library & Vector Ingestion Workspace.
    Features:
    - Official JA Assure PDF Catalog & ChromaDB Status
    - Live PDF Document Ingestion & Chunking
    - ChromaDB Vector Store Statistics
    - Searchable Page Chunks Explorer
    """
    st.markdown("### JA Assure Knowledge Library (Tier 1)")
    st.caption("Official underwriting guides and product architecture PDFs indexed in local ChromaDB for RAG grounding.")

    from backend.knowledge.vector_store import vector_store
    from backend.knowledge.pdf_pipeline import pdf_pipeline
    import os

    # 1. Knowledge Tier Metric Strip
    stats = vector_store.get_company_knowledge_stats()
    total_chunks = stats.get("total_chunks", 0)
    indexed_docs = stats.get("indexed_documents", [])

    kcol1, kcol2, kcol3 = st.columns(3)
    with kcol1:
        st.metric("Indexed Chunks in ChromaDB", total_chunks)
    with kcol2:
        st.metric("Authoritative Documents", len(indexed_docs))
    with kcol3:
        st.metric("Vector Store Engine", "ChromaDB (Offline L2)")

    st.markdown("---")

    # 2. PDF Document Ingestion & Upload Section
    st.markdown("#### Ingest Official Knowledge PDF")
    up_col1, up_col2 = st.columns([2.5, 1.5])

    with up_col1:
        uploaded_pdf = st.file_uploader(
            "Upload Official JA Assure PDF Document",
            type=["pdf"],
            help="Extracts text per page, chunks with overlap, tags product metadata, and indexes in ChromaDB.",
            key="pdf_uploader_widget",
        )
        if uploaded_pdf is not None:
            save_path = Path("data/knowledge/pdfs") / uploaded_pdf.name
            with open(save_path, "wb") as f:
                f.write(uploaded_pdf.getbuffer())
            with st.spinner(f"Processing and indexing {uploaded_pdf.name}..."):
                chunks = pdf_pipeline.ingest_pdf(save_path)
                vector_store.index_pdf_chunks(chunks)
                st.success(f"✓ Successfully indexed {len(chunks)} page-aware chunks from '{uploaded_pdf.name}' into ChromaDB!")
                st.rerun()

    with up_col2:
        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.85rem; font-size: 0.76rem; color: #475569;">
                <b>PDF Ingestion Pipeline:</b>
                <ol style="margin-top: 0.35rem; padding-left: 1.1rem; line-height: 1.4;">
                    <li>Multi-page text extraction</li>
                    <li>Page-level metadata preservation</li>
                    <li>500-char sliding chunking (100-char overlap)</li>
                    <li>ChromaDB vector embedding</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔄 Re-Index All Seed PDFs", key="btn_reindex_all_pdfs", use_container_width=True):
            with st.spinner("Extracting and embedding all knowledge PDFs..."):
                all_chunks = pdf_pipeline.ingest_all_pdfs()
                vector_store.index_pdf_chunks(all_chunks)
                st.toast(f"Re-indexed {len(all_chunks)} chunks across all official PDFs!")
                st.rerun()

    st.markdown("---")

    # 3. Active Authoritative Document Registry
    st.markdown("#### Authoritative JA Assure Knowledge Repository")
    
    tab_docs, tab_chunks, tab_legacy = st.tabs(["📄 Indexed PDF Documents", "🔍 Page Chunks Explorer", "🌐 Web Knowledge Mirror"])

    with tab_docs:
        if not indexed_docs:
            st.info("No PDFs currently indexed. Click 'Re-Index All Seed PDFs' to index repository seed documents.")
        else:
            for doc in indexed_docs:
                fn = doc.get("filename", "")
                prod = doc.get("product", "Specialty Insurance")
                brand = doc.get("brand", "JA Assure")
                pages = doc.get("total_pages", 1)
                chunks_count = doc.get("chunk_count", 1)

                border_color = "#D4AF37" if brand == "Jade" else ("#0D9488" if brand == "DoctorShield" else "#3B82F6")

                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {border_color}; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <div style="font-size: 0.98rem; font-weight: 800; color: #0F172A;">{fn}</div>
                            <span class="pill-badge pill-neutral">{brand}</span>
                        </div>
                        <div style="font-size: 0.76rem; color: #64748B; margin: 0.25rem 0;">Product Line: <b>{prod}</b></div>
                        <div style="display: flex; gap: 1.5rem; font-size: 0.75rem; color: #334155; margin-top: 0.4rem;">
                            <span><b>Pages:</b> {pages}</span>
                            <span><b>ChromaDB Chunks:</b> {chunks_count}</span>
                            <span style="color: #10B981; font-weight: 700;">✓ Active in Tier 1 RAG</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with tab_chunks:
        st.caption("Search across individual indexed page chunks stored in ChromaDB.")
        chunk_query = st.text_input("Search PDF Chunks", placeholder="e.g. vault alarm, unattended vehicle, clinical malpractice...", key="chunk_search_input")
        if chunk_query:
            matches = vector_store.hybrid_search(chunk_query, top_k=5)
            st.markdown(f"Found **{len(matches)}** matching chunks:")
            for m in matches:
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.65rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                            <span>📄 {m['filename']} (Page {m['page_number']}) — {m['section']}</span>
                            <span style="color: #2563EB;">Score: {m['relevance_score']}</span>
                        </div>
                        <div style="font-size: 0.76rem; color: #475569; margin-top: 0.45rem; line-height: 1.45; white-space: pre-line;">
                            {m['text']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Enter keywords above to explore how ChromaDB retrieves page-level citations for ContentAgent prompts.")

    with tab_legacy:
        sources = load_all_sources()
        for s in sources:
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.65rem;">
                        <div style="font-weight: 700; color: #0F172A; font-size: 0.90rem;">{s.get('title')}</div>
                        <div style="font-size: 0.74rem; color: #64748B;">{s.get('vertical')}</div>
                        <div style="font-size: 0.78rem; color: #334155; margin: 0.35rem 0;">{s.get('summary')}</div>
                        <div style="font-size: 0.70rem; color: #2563EB;">URL: <a href="{s.get('url')}" target="_blank">{s.get('url')}</a></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

