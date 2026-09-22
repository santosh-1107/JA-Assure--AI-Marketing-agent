"""
Feedback & Learning Component for JA Assure.
Provides the closed-loop learning analytics workspace and the right-rail feedback stream widget.
"""

import pandas as pd
import streamlit as st
from typing import Any, Dict, List
from backend import models
from backend.agents.feedback_agent import feedback_agent


def render_feedback_right_widget():
    """
    Renders the right-rail 'Recent Feedback' card matching the reference image:
    - 3 recent corrections with colored category pills and reviewer notes
    - 'View All Feedback →' CTA button
    """
    all_fb = models.list_all_feedback(limit=4)

    st.markdown(
        f"""
        <div class="right-widget-card">
            <div class="widget-header">
                <span style="font-size: 1.1rem; color: #2563EB;">💬</span>
                <div>
                    <div class="widget-title">Recent Feedback</div>
                    <div class="widget-sub">{len(models.list_all_feedback())} total corrections</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for fb in all_fb[:3]:
        tag = fb.get("tag", "inaccurate_claim")
        tag_color = "#DC2626" if "inaccurate" in tag else ("#7C3AED" if "salesy" in tag else "#D97706")
        tag_bg = "#FEE2E2" if "inaccurate" in tag else ("#F3E8FF" if "salesy" in tag else "#FEF3C7")
        time_ago = fb.get("created_at", "")[:16]

        st.markdown(
            f"""
            <div class="feedback-stream-item">
                <div class="fb-tag-row">
                    <span style="background: {tag_bg}; color: {tag_color}; font-size: 0.68rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px;">
                        {tag}
                    </span>
                    <span style="font-size: 0.68rem; color: #94A3B8;">{time_ago}</span>
                </div>
                <div class="fb-text">"{fb.get('note')}"</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("View All Feedback →", key="btn_view_all_fb", use_container_width=True):
        st.session_state["active_page"] = "Feedback & Learning"
        st.rerun()


from backend.database import is_demo_mode
from backend.services.analytics_service import get_dashboard_metrics


def render_feedback_learning_page():
    """
    Renders full Feedback & Learning analytics workspace.
    Derives all rejection trends and metrics strictly from SQLite records.
    """
    st.markdown("### Feedback & Learning")
    st.caption("Reviewer decisions become structured learning signals for future generations.")

    db_metrics = get_dashboard_metrics()
    stats = feedback_agent.get_rejection_rate_analytics()
    all_fb = models.list_all_feedback()
    latest_rate = db_metrics.get("latest_cycle_rejection_rate")
    rate_display = f"{latest_rate}%" if latest_rate is not None else "0.0%"

    # Top metrics row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Review Cycles", len(stats.get("cycles", [])))
    with c2:
        st.metric("Total Corrections", len(all_fb))
    with c3:
        st.metric("Current Rejection Rate", rate_display)
    with c4:
        rel_red = db_metrics.get("relative_error_reduction")
        delta_pts = db_metrics.get("rejection_rate_delta")
        if rel_red is not None:
            delta_str = f"{delta_pts}% pts" if delta_pts is not None else None
            st.metric("Relative Error Reduction", f"{rel_red}%", delta=delta_str)
        else:
            st.metric("Relative Error Reduction", "—", delta=None)

    st.markdown("---")

    # 1. Rejection Rate by Generation Cycle Line Chart
    st.markdown("#### Rejection Rate by Generation Cycle")
    st.caption("Empirical proof that reviewer corrections reduce compliance violations over successive review cycles.")

    cycles = stats.get("cycles", [])
    if cycles:
        df_cycles = pd.DataFrame(cycles)
        df_cycles["Cycle Label"] = df_cycles["cycle"].apply(lambda c: f"Cycle {c}")
        col_c1, col_c2 = st.columns([2.5, 1])
        with col_c1:
            st.line_chart(df_cycles.set_index("Cycle Label")["rejection_rate"], color="#D4AF37", height=240)
        with col_c2:
            if is_demo_mode():
                st.markdown(
                    """
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; font-size: 0.80rem;">
                        <span style="background: #FEF3C7; color: #92400E; font-size: 0.65rem; font-weight: 800; padding: 0.15rem 0.4rem; border-radius: 3px;">DEMO DATA</span>
                        <div style="margin-top: 0.4rem; font-weight: 700; color: #0F172A;">Demo Benchmark Progression:</div>
                        <div style="margin-top: 0.35rem; color: #475569; line-height: 1.5;">
                            • Cycle 1: 80.0% rejected (baseline)<br/>
                            • Cycle 2: 60.0% rejected (rules applied)<br/>
                            • Cycle 3: 40.0% rejected (nuance learned)<br/>
                            • Cycle 4: 20.0% rejected (high precision)<br/>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                cycle_items_html = "".join([
                    f"• Cycle {c['cycle']}: {c['rejection_rate']}% ({c['rejected']}/{c['total']} rejected)<br/>"
                    for c in cycles
                ])
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; font-size: 0.80rem;">
                        <div style="font-weight: 700; color: #0F172A;">Live Cycle Progression:</div>
                        <div style="margin-top: 0.35rem; color: #475569; line-height: 1.5;">
                            {cycle_items_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No completed review cycles on record in the current database.")

    st.markdown("---")

    # 2. Before & After Showcase
    st.markdown("#### Before & After Learning Showcase")
    st.caption("Side-by-side evidence of original rejected content versus regenerated compliant copy.")

    pairs = models.get_before_after_pairs(limit=4)
    if pairs:
        for p in pairs:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.15rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span class="pill-badge pill-neutral">{p['brand']} • {p['platform']}</span>
                        <span style="font-size: 0.72rem; color: #64748B;">Parent #{p['parent_id']} ➔ Variant #{p['child_id']}</span>
                    </div>
                    <div style="background: #FEF3C7; border: 1px solid #FDE68A; border-radius: 4px; padding: 0.4rem 0.65rem; font-size: 0.76rem; color: #92400E; margin-bottom: 0.75rem;">
                        💡 <b>Reviewer Correction Injected:</b> [{p.get('feedback_tag')}] {p.get('feedback_note')}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; padding: 0.85rem;">
                            <div style="font-size: 0.74rem; font-weight: 800; color: #DC2626; margin-bottom: 0.35rem;">❌ BEFORE (REJECTED)</div>
                            <div style="font-size: 0.80rem; color: #334155; line-height: 1.45;">{p['original_content']}</div>
                        </div>
                        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 0.85rem;">
                            <div style="font-size: 0.74rem; font-weight: 800; color: #059669; margin-bottom: 0.35rem;">✅ AFTER (REGENERATED COMPLIANT)</div>
                            <div style="font-size: 0.80rem; color: #334155; line-height: 1.45;">{p['regenerated_content']}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 3. Semantic Feedback Retrieval Explorer
    st.markdown("#### 🧠 Semantic Feedback Search & Memory Inspection")
    st.caption("Inspect how ChromaDB vector embeddings match incoming marketing drafts against historical reviewer corrections.")

    from backend.knowledge.vector_store import vector_store

    sem_col1, sem_col2 = st.columns([3, 1])
    with sem_col1:
        sem_query = st.text_input(
            "Test Marketing Copy / Prohibited Claim",
            value="We guarantee full loss recovery on high-value jewelry in transit",
            placeholder="Type a draft sentence to retrieve similar past rejections...",
            key="sem_feedback_query",
        )
    with sem_col2:
        sem_brand = st.selectbox("Filter Brand", ["All Brands", "Jade", "DoctorShield"], key="sem_fb_brand")

    b_filter = None if sem_brand == "All Brands" else sem_brand
    if sem_query:
        matches = vector_store.search_similar_feedback(query=sem_query, brand=b_filter, top_k=3)
        if matches:
            st.markdown(f"Found **{len(matches)}** semantically similar historical correction(s):")
            for m in matches:
                sim_pct = int(m.get("similarity_score", 0.0) * 100)
                tag_label = m.get("issue_type") or m.get("tag") or m.get("rejection_tag") or "Correction"
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #F59E0B; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.65rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                            <span style="background: #FEF3C7; color: #92400E; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px;">
                                [{tag_label}] {m.get('brand')}
                            </span>
                            <span style="color: #D97706; font-weight: 800; font-size: 0.76rem;">
                                Semantic Match: {sim_pct}%
                            </span>
                        </div>
                        <div style="font-size: 0.80rem; color: #0F172A; font-weight: 600;">
                            Reviewer Directive: "{m.get('reviewer_note')}"
                        </div>
                        <div style="font-size: 0.74rem; color: #64748B; margin-top: 0.25rem;">
                            Rule Reference: {m.get('compliance_rule') or 'JA Assure Governance Standard'}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No matching feedback embeddings found in ChromaDB for this phrase.")

    st.markdown("---")

    # 4. Learning Signals & Audit Trail Table
    st.markdown("#### Reviewer Feedback Audit Trail")
    if all_fb:
        df_fb = pd.DataFrame([
            {
                "ID": f"#{f['id']}",
                "Asset": f"#{f.get('content_id')}",
                "Brand": f["brand"],
                "Category Tag": f["tag"],
                "Reviewer Note": f["note"],
                "Timestamp": f["created_at"][:16] if f.get("created_at") else "",
            }
            for f in all_fb
        ])
        st.dataframe(df_fb, use_container_width=True, hide_index=True)

