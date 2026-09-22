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
    Renders the full dedicated Knowledge Library page.
    """
    st.markdown("### JA Assure Knowledge Library")
    st.caption("Approved official knowledge sources used to ground all AI marketing content and ensure anti-hallucination compliance.")

    sources = load_all_sources()
    k_query = st.text_input("Filter Documents", placeholder="Search by title, keyword, or insurance vertical...", label_visibility="collapsed")

    filtered = []
    for s in sources:
        if k_query and k_query.strip():
            q = k_query.lower()
            text = (s.get("title", "") + " " + s.get("summary", "") + " " + " ".join(s.get("keywords", []))).lower()
            if q not in text:
                continue
        filtered.append(s)

    for doc in filtered:
        with st.container():
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.15rem; margin-bottom: 0.85rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <div style="font-size: 1.02rem; font-weight: 800; color: #0F172A;">{doc.get('title')}</div>
                        <span class="pill-badge pill-neutral">{doc.get('brand', 'General')}</span>
                    </div>
                    <div style="font-size: 0.74rem; color: #64748B; margin: 0.25rem 0 0.5rem 0;">Line: <b>{doc.get('vertical')}</b></div>
                    <div style="font-size: 0.84rem; color: #334155; line-height: 1.5; margin-bottom: 0.75rem;">
                        {doc.get('summary')}
                    </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Underwriting Facts & Official Reference", expanded=False):
                st.markdown(f"**Source URL:** [{doc.get('url')}]({doc.get('url')})")
                st.markdown("**Grounding Key Facts:**")
                for kf in doc.get("key_facts", []):
                    st.markdown(f"- {kf}")
            st.markdown("</div>", unsafe_allow_html=True)
