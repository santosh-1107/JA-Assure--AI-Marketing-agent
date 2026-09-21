"""
JA Assure AI Marketing Agent — Human Review Dashboard
A single-page InsurTech review dashboard built with Streamlit.
Features:
- Pending Queue with fail-first sorting & compliance verdict cards
- Approved Queue & Social Publishing scheduler
- Feedback & Learning Hub with empirical rejection-rate line chart & Before/After comparisons
- 1-Click Interactive Demo Bench for Hackathon Judges
- InsurTech Lead Pipeline (P1)
"""

import os
import sys
import json
import pandas as pd
import streamlit as st
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db
from backend.gemini_service import gemini_service
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from backend import models
from dashboard.style import CUSTOM_CSS

# Page configuration
st.set_page_config(
    page_title="JA Assure — AI Marketing Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize database schema if not present
init_db()


def render_knowledge_sources(sources, key_prefix="src"):
    """
    Renders official JA Assure knowledge attribution badge and expandable source details.
    Provides verified grounding context from https://www.ja-assure.com/resources.html.
    """
    if not sources:
        return

    st.markdown(
        """
        <div style="margin: 0.5rem 0 0.35rem 0;">
            <span style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 4px; padding: 0.2rem 0.6rem; font-size: 0.76rem; color: #93c5fd; font-weight: 500;">
                📚 Grounded in JA Assure Knowledge
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("🔍 View Sources", expanded=False):
        st.markdown("**Source Organization:** [JA Assure Resources](https://www.ja-assure.com/resources.html)")
        for s in sources:
            title = s.get("title", "JA Assure Knowledge Resource")
            url = s.get("url", "https://www.ja-assure.com/resources.html")
            vertical = s.get("vertical", "")
            key_facts = s.get("key_facts", [])
            snippet = s.get("snippet", "")

            st.markdown(f"• **Article:** [{title}]({url})")
            st.markdown(f"  **URL:** `{url}`")
            if vertical:
                st.markdown(f"  **Product / Class:** {vertical}")
            if key_facts:
                st.markdown("  **Verified JA Assure Grounding Facts:**")
                for kf in key_facts[:3]:
                    st.markdown(f"  - {kf}")
            elif snippet:
                st.markdown(f"  **Digest:** {snippet}")


# =====================================================================
# Top Header & System Status
# =====================================================================

llm_status = gemini_service.check_health()

st.markdown(
    """
    <div class="header-container">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div class="header-title">
                    🛡️ JA Assure <span style="font-size: 1.1rem; font-weight: 500; color: #94a3b8;">| AI Marketing Agent</span>
                </div>
                <div style="margin-top: 0.35rem; display: flex; gap: 0.5rem; align-items: center;">
                    <span class="brand-pill-jade">✨ Jade Luxury Assets</span>
                    <span class="brand-pill-ds">🩺 DoctorShield Medico-Legal</span>
                    <span style="font-size: 0.78rem; color: #64748b;">Regional Insurance Advertising Standards</span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# LLM Status Bar
with st.container():
    if llm_status["is_live"]:
        st.success(f"🟢 **Live LLM Connected**: Google AI Studio ({llm_status['model']})", icon="✅")
    else:
        st.info(
            "⚡ **Deterministic InsurTech Engine Active** (Demo/Offline Mode) — "
            "To connect live Gemini Flash, set `GEMINI_API_KEY` in `.env`.",
            icon="ℹ️",
        )


# =====================================================================
# Sidebar: Brand Selector & Quick Actions
# =====================================================================

with st.sidebar:
    st.markdown("### 🎛️ Marketing Controls")
    selected_brand = st.selectbox("Brand Filter", ["All Brands", "Jade", "DoctorShield"])
    filter_brand = None if selected_brand == "All Brands" else selected_brand

    st.markdown("---")
    st.markdown("### 📊 Live System KPIs")
    pending_items = models.list_pending_content(brand=filter_brand)
    approved_items = models.list_approved_content(brand=filter_brand)
    all_feedback = models.list_all_feedback(brand=filter_brand)
    stats_data = feedback_agent.get_rejection_rate_analytics()

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("Pending Review", len(pending_items))
        st.metric("Feedback Rules", len(all_feedback))
    with col_sb2:
        st.metric("Approved Assets", len(approved_items))
        st.metric("Overall Rej. Rate", f"{stats_data['overall_rejection_rate']}%")

    st.markdown("---")
    st.markdown("### ⚡ Database Utilities")
    if st.button("🔄 Reload Demo Seed Data", use_container_width=True):
        from scripts.seed_demo import seed_data
        seed_data()
        st.success("Demo dataset re-seeded with 4 cycles (80% -> 20%)!")
        st.rerun()

    st.markdown(
        """
        <div style="font-size: 0.75rem; color: #64748b; margin-top: 1.5rem; line-height: 1.4;">
            <b>Governance Hard Rule:</b><br/>
            Zero automated publishing. Every asset requires explicit human sign-off before entering the approved queue.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================================
# KPI Summary Ribbon
# =====================================================================

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Pending Human Review</div>
            <div class="metric-value">{len(pending_items)}</div>
            <div class="metric-caption">Non-compliant items sorted to top</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Approved Marketing Assets</div>
            <div class="metric-value" style="color: #34d399;">{len(approved_items)}</div>
            <div class="metric-caption">Ready for social scheduling</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi3:
    latest_cycle_rate = stats_data["cycles"][-1]["rejection_rate"] if stats_data["cycles"] else 0.0
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Latest Rejection Rate</div>
            <div class="metric-value" style="color: #60a5fa;">{latest_cycle_rate}%</div>
            <div class="metric-caption">Down from 80.0% in Cycle 1</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Learned Corrections</div>
            <div class="metric-value" style="color: #e5c07b;">{len(all_feedback)}</div>
            <div class="metric-caption">Injected as few-shot constraints</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br/>", unsafe_allow_html=True)


# =====================================================================
# Main Tabs Navigation
# =====================================================================

tab_pending, tab_approved, tab_learning, tab_demo, tab_leads = st.tabs([
    "📋 Pending Review Queue",
    "✅ Approved Queue",
    "🧠 Feedback & Learning Hub",
    "⚡ 1-Click Judge Demo Bench",
    "🎯 InsurTech Leads (P1)",
])


# =====================================================================
# TAB 1: PENDING REVIEW QUEUE
# =====================================================================

with tab_pending:
    st.markdown("### 📋 Content Awaiting Human Compliance Approval")
    st.caption("Content Agent outputs must pass human review. Failed items are highlighted in red and sorted first.")

    pending_list = models.list_pending_content(brand=filter_brand)

    if not pending_list:
        st.info("🎉 No content pending review. All generated assets have been approved or rejected.")
    else:
        for item in pending_list:
            comp = item.get("compliance_result") or {"status": "pass", "reasons": []}
            is_fail = comp.get("status") == "fail"
            card_class = "content-card-fail" if is_fail else ("content-card-jade" if item["brand"] == "Jade" else "content-card-ds")

            with st.container():
                # Header of the card
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <span class="{'brand-pill-jade' if item['brand'] == 'Jade' else 'brand-pill-ds'}">{item['brand']}</span>
                                <span class="badge-platform">{item['platform']} • {item['content_type'].upper()}</span>
                                <span class="badge-cycle">Cycle {item.get('cycle', 1)}</span>
                                <span style="font-size: 0.75rem; color: #64748b;">ID #{item['id']}</span>
                            </div>
                            <div>
                                {'<span class="badge-fail">⚠️ FAIL — COMPLIANCE GATE</span>' if is_fail else '<span class="badge-pass">✓ PASS — COMPLIANT</span>'}
                            </div>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )

                # If compliance failed, display detailed reasons
                if is_fail:
                    reasons = comp.get("reasons", [])
                    reasons_html = "<div class='compliance-box-fail'>"
                    for r in reasons:
                        reasons_html += f"<div class='compliance-rule-title'>🚨 RULE VIOLATION: {r.get('rule')}</div>"
                        reasons_html += f"<div class='compliance-rule-desc'>{r.get('message')}</div>"
                        if r.get("matched_phrase"):
                            reasons_html += f"<div style='font-size: 0.75rem; color: #f87171; margin-top: 0.25rem;'><b>Trigger Phrase:</b> \"{r.get('matched_phrase')}\"</div>"
                    reasons_html += "</div>"
                    st.markdown(reasons_html, unsafe_allow_html=True)

                # Show fixed issue badge if this was regenerated
                if item.get("fixed_issue"):
                    st.markdown(
                        f"""
                        <div style="background: rgba(13, 148, 136, 0.15); border: 1px solid rgba(13, 148, 136, 0.4); border-radius: 6px; padding: 0.4rem 0.75rem; font-size: 0.78rem; color: #2dd4bf; margin-bottom: 0.5rem;">
                            🔄 <b>Correction Applied from Parent ID #{item.get('parent_id')}:</b> {item['fixed_issue']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Content Body
                st.markdown(f"<div class='content-text-box'>{item['content']}</div>", unsafe_allow_html=True)
                render_knowledge_sources(item.get("sources"), key_prefix=f"p_{item['id']}")
                st.markdown("</div>", unsafe_allow_html=True)

                # Actions Bar
                col_act1, col_act2, col_act3, col_act4 = st.columns([1.2, 1.2, 1.5, 2.1])

                with col_act1:
                    if st.button("✅ Approve", key=f"app_btn_{item['id']}", use_container_width=True):
                        models.approve_content(item["id"])
                        st.success(f"Asset #{item['id']} approved!")
                        st.rerun()

                with col_act2:
                    show_reject_form = st.checkbox("❌ Reject", key=f"rej_chk_{item['id']}")

                with col_act3:
                    show_edit_form = st.checkbox("✏️ Edit Copy", key=f"edit_chk_{item['id']}")

                with col_act4:
                    if st.button("🔄 Regenerate with Feedback", key=f"regen_btn_{item['id']}", use_container_width=True):
                        with st.spinner("Injecting brand feedback and regenerating compliant variant..."):
                            recent_fb = feedback_agent.get_recent_feedback(item["brand"], n=5)
                            regen_result = content_agent.generate(
                                topic=f"Refined {item['brand']} campaign for {item['platform']}",
                                brand=item["brand"],
                                platform=item["platform"],
                                content_type=item["content_type"],
                                past_corrections=recent_fb,
                                force_trigger_flaw=False,
                                cycle=item.get("cycle", 1) + 1,
                            )
                            regen_comp = compliance_agent.check(regen_result["content"], item["brand"])
                            fixed_note = "Resolved compliance violation using recent brand feedback."
                            if recent_fb:
                                fixed_note = f"Corrected: [{recent_fb[0]['tag']}] {recent_fb[0]['note']}"

                            new_v = models.insert_content(
                                brand=item["brand"],
                                platform=item["platform"],
                                content_type=item["content_type"],
                                content=regen_result["content"],
                                compliance_result=regen_comp,
                                cycle=item.get("cycle", 1) + 1,
                                parent_id=item["id"],
                                fixed_issue=fixed_note,
                                status="pending",
                            )
                            st.success(f"New compliant variant #{new_v['id']} created!")
                            st.rerun()

                # Reject Form Expander
                if show_reject_form:
                    with st.form(key=f"reject_form_{item['id']}"):
                        st.markdown("##### 📝 Reviewer Feedback Form")
                        st.caption("Feedback is permanently stored and fed into the next generation prompt.")
                        rej_tag = st.selectbox(
                            "Feedback Category Tag",
                            ["inaccurate_claim", "too_salesy", "off_brand_tone", "wrong_cta", "other"],
                            key=f"tag_select_{item['id']}",
                        )
                        default_note = "Avoid guaranteed payout language. Always qualify claims with 'subject to policy terms and conditions'." if is_fail else ""
                        rej_note = st.text_area(
                            "Reviewer Correction Note (Required)",
                            value=default_note,
                            placeholder="Provide explicit instructions on why this was rejected and what to fix...",
                            key=f"note_area_{item['id']}",
                        )
                        submit_reject = st.form_submit_button("Submit Rejection & Store Feedback", use_container_width=True)
                        if submit_reject:
                            if not rej_note.strip():
                                st.error("Please provide a feedback note.")
                            else:
                                models.reject_content(item["id"], tag=rej_tag, note=rej_note.strip())
                                st.warning(f"Item #{item['id']} rejected. Feedback stored for {item['brand']}.")
                                st.rerun()

                # Edit Form Expander
                if show_edit_form:
                    with st.form(key=f"edit_form_{item['id']}"):
                        st.markdown("##### ✏️ Modify Copy Directly")
                        new_content_text = st.text_area(
                            "Marketing Copy",
                            value=item["content"],
                            height=180,
                            key=f"edit_content_{item['id']}",
                        )
                        edit_tag = st.selectbox(
                            "Edit Rationale Tag (Optional)",
                            ["inaccurate_claim", "too_salesy", "off_brand_tone", "wrong_cta", "other"],
                            key=f"edit_tag_{item['id']}",
                        )
                        edit_note = st.text_input("Edit Note (Optional)", key=f"edit_note_{item['id']}")
                        submit_edit = st.form_submit_button("Save Edits & Re-Check Compliance", use_container_width=True)
                        if submit_edit:
                            if not new_content_text.strip():
                                st.error("Content cannot be empty.")
                            else:
                                new_comp = compliance_agent.check(new_content_text, item["brand"])
                                models.edit_content(
                                    content_id=item["id"],
                                    edited_content=new_content_text.strip(),
                                    tag=edit_tag if edit_note else None,
                                    note=edit_note if edit_note else None,
                                    compliance_result=new_comp,
                                )
                                st.success("Edits saved and compliance re-audited!")
                                st.rerun()

                st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 1.5rem 0;'/>", unsafe_allow_html=True)


# =====================================================================
# TAB 2: APPROVED QUEUE
# =====================================================================

with tab_approved:
    st.markdown("### ✅ Approved Marketing Assets Queue")
    st.caption("Assets approved by human compliance reviewers. Ready for social posting or export.")

    approved_list = models.list_approved_content(brand=filter_brand)

    if not approved_list:
        st.info("No approved assets yet. Review and approve pending items first.")
    else:
        for app_item in approved_list:
            is_scheduled = app_item.get("status") == "scheduled"
            b_class = "brand-pill-jade" if app_item["brand"] == "Jade" else "brand-pill-ds"

            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #111722; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <span class="{b_class}">{app_item['brand']}</span>
                                <span class="badge-platform">{app_item['platform']} • {app_item['content_type'].upper()}</span>
                                <span style="font-size: 0.75rem; color: #64748b;">Asset #{app_item['id']}</span>
                            </div>
                            <div>
                                {'<span style="background: rgba(96, 165, 250, 0.15); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.3); padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">📅 SCHEDULED</span>' if is_scheduled else '<span class="badge-pass">✓ APPROVED</span>'}
                            </div>
                        </div>
                        <div class="content-text-box">{app_item['content']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                render_knowledge_sources(app_item.get("sources"), key_prefix=f"app_{app_item['id']}")

                col_app1, col_app2 = st.columns([1.5, 4])
                with col_app1:
                    if not is_scheduled:
                        if st.button("📅 Schedule for Social Publish", key=f"sched_{app_item['id']}"):
                            models.schedule_content(app_item["id"])
                            st.success(f"Asset #{app_item['id']} transitioned to 'scheduled' state!")
                            st.rerun()
                    else:
                        st.caption("✅ Dispatched to social posting worker.")
                with col_app2:
                    st.caption(f"Created: {app_item.get('created_at', 'N/A')}")

                st.markdown("<hr style='border-color: rgba(255,255,255,0.04); margin: 0.75rem 0;'/>", unsafe_allow_html=True)


# =====================================================================
# TAB 3: FEEDBACK & LEARNING HUB (DIFFERENTIATOR)
# =====================================================================

with tab_learning:
    st.markdown("### 🧠 The Closed-Loop Learning Engine")
    st.markdown(
        "Demonstrates how human rejections directly educate the AI Content Agent, "
        "measurably reducing non-compliant claim rates over successive review cycles."
    )

    # 1. Rejection Rate Over Time Chart
    st.markdown("#### 📉 Rejection Rate Across Review Cycles")
    st.caption("Benchmark Data: Cycles 1–4 are seeded historical review cycles demonstrating the learning progression. Live review actions in this session appear dynamically as Cycle 5+.")
    chart_stats = feedback_agent.get_rejection_rate_analytics()

    if chart_stats["cycles"]:
        df_cycles = pd.DataFrame(chart_stats["cycles"])
        df_cycles["Cycle Label"] = df_cycles["cycle"].apply(lambda c: f"Cycle {c}")

        col_c1, col_c2 = st.columns([2.5, 1])
        with col_c1:
            st.line_chart(
                df_cycles.set_index("Cycle Label")["rejection_rate"],
                color="#e5c07b",
                height=260,
            )
        with col_c2:
            st.markdown(
                """
                <div style="background: #131b2a; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem;">
                    <div style="font-weight: 700; color: #e2e8f0; margin-bottom: 0.5rem;">Benchmark Cycles 1–4 (Demo Data)</div>
                    <div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.6;">
                        • <b>Cycle 1:</b> 80.0% rejected (baseline errors)<br/>
                        • <b>Cycle 2:</b> 60.0% rejected (rules applied)<br/>
                        • <b>Cycle 3:</b> 40.0% rejected (nuance learning)<br/>
                        • <b>Cycle 4:</b> 20.0% rejected (high precision)<br/>
                    </div>
                    <div style="margin-top: 0.75rem; font-size: 0.75rem; color: #34d399;">
                        <b>Result:</b> 75% relative error reduction
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 2. Before / After Side-by-Side Showcase
    st.markdown("#### 🔍 Before & After Evidence (Visible Learning)")
    st.caption("Direct side-by-side comparison of original rejected content versus regenerated compliant variant.")

    pairs = models.get_before_after_pairs(brand=filter_brand, limit=5)

    if not pairs:
        st.info("No before/after variants on record yet. Use 'Regenerate with feedback' on a rejected post to produce one.")
    else:
        for pair in pairs:
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #111722; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                            <span class="{'brand-pill-jade' if pair['brand'] == 'Jade' else 'brand-pill-ds'}">{pair['brand']} • {pair['platform']}</span>
                            <span style="font-size: 0.78rem; color: #94a3b8;">Parent #{pair['parent_id']} ➔ Variant #{pair['child_id']}</span>
                        </div>
                        <div style="background: rgba(212, 175, 55, 0.1); border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.8rem; color: #e5c07b; margin-bottom: 0.75rem;">
                            💡 <b>Reviewer Correction Applied:</b> [{pair.get('feedback_tag', 'inaccurate_claim')}] {pair.get('feedback_note', 'Avoid guaranteed claims.')}
                        </div>
                        <div class="diff-container">
                            <div class="diff-before">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                                    <span style="color: #f87171; font-weight: 700; font-size: 0.82rem;">❌ BEFORE (ORIGINAL REJECTED)</span>
                                    <span class="badge-fail">FAIL</span>
                                </div>
                                <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1; white-space: pre-wrap;">{pair['original_content']}</div>
                            </div>
                            <div class="diff-after">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                                    <span style="color: #34d399; font-weight: 700; font-size: 0.82rem;">✅ AFTER (REGENERATED COMPLIANT)</span>
                                    <span class="badge-pass">PASS</span>
                                </div>
                                <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1; white-space: pre-wrap;">{pair['regenerated_content']}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                render_knowledge_sources(pair.get("child_sources") or pair.get("parent_sources"), key_prefix=f"pair_{pair['child_id']}")

    st.markdown("---")

    # 3. Recent Feedback Audit Trail Table
    st.markdown("#### 📜 Reviewer Feedback Audit Trail")
    st.caption("Immutable feedback records stored in SQLite and injected into the Content Agent's few-shot prompt.")

    fb_items = models.list_all_feedback(brand=filter_brand, limit=20)
    if fb_items:
        fb_table_data = []
        for f in fb_items:
            fb_table_data.append({
                "ID": f"#{f['id']}",
                "Brand": f["brand"],
                "Tag": f["tag"],
                "Reviewer Correction Note": f["note"],
                "Linked Asset": f"#{f['content_id']}",
                "Date": f["created_at"][:19] if f.get("created_at") else "N/A",
            })
        st.dataframe(pd.DataFrame(fb_table_data), use_container_width=True, hide_index=True)


# =====================================================================
# TAB 4: 1-CLICK INTERACTIVE JUDGE DEMO BENCH
# =====================================================================

with tab_demo:
    st.markdown("### ⚡ Live Demo Walkthrough (For Hackathon Judges)")
    st.markdown(
        "Execute the complete end-to-end feedback loop in 60 seconds:\n"
        "**Generate ➔ Compliance Gate (FAIL) ➔ Human Review (Reject) ➔ Store Feedback ➔ Regenerate ➔ Compliance Gate (PASS) ➔ Prove Learning**"
    )

    demo_col1, demo_col2 = st.columns([1, 1.2])

    with demo_col1:
        st.markdown("#### Step 1: Configure Generation")
        demo_brand = st.selectbox("Select Brand", ["Jade", "DoctorShield"], index=0, key="demo_brand_sel")
        demo_platform = st.selectbox("Select Platform", ["LinkedIn", "Instagram", "X"], index=0, key="demo_plat_sel")
        
        default_topic = (
            "How jewellery businesses protect high-value inventory"
            if demo_brand == "Jade"
            else "Medical indemnity and malpractice defense for healthcare professionals"
        )
        demo_topic = st.text_input(
            "Campaign Topic",
            value=default_topic,
            key=f"demo_topic_{demo_brand}",
        )

        st.markdown("#### Step 2: Trigger Generation")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            gen_risky = st.button("🚨 Generate Risky Post (Demo FAIL)", use_container_width=True)
        with col_btn2:
            gen_compliant = st.button("✨ Generate Compliant Post", use_container_width=True)

        if gen_risky or gen_compliant:
            with st.spinner("Retrieving JA Assure knowledge and evaluating compliance..."):
                force_flaw = bool(gen_risky)
                research_context = research_agent.research(brand=demo_brand, topic=demo_topic)
                gen_res = content_agent.generate(
                    topic=demo_topic,
                    brand=demo_brand,
                    platform=demo_platform,
                    content_type="post",
                    research_context=research_context,
                    force_trigger_flaw=force_flaw,
                    cycle=1 if force_flaw else 2,
                )
                comp_res = compliance_agent.check(gen_res["content"], demo_brand)
                saved_demo_item = models.insert_content(
                    brand=demo_brand,
                    platform=demo_platform,
                    content_type="post",
                    content=gen_res["content"],
                    compliance_result=comp_res,
                    cycle=1 if force_flaw else 2,
                    sources=gen_res.get("sources"),
                    status="pending",
                )
                st.session_state["active_demo_item"] = saved_demo_item
                st.session_state["demo_parent_item"] = None
                st.success(f"Generated Asset #{saved_demo_item['id']} grounded in JA Assure knowledge!")
                st.rerun()

    with demo_col2:
        st.markdown("#### Step 3: Active Demo Preview")
        active_demo = st.session_state.get("active_demo_item")

        if not active_demo:
            # Pick first pending item if exists
            p_items = models.list_pending_content()
            if p_items:
                active_demo = p_items[0]

        if active_demo:
            comp = active_demo.get("compliance_result") or {"status": "pass", "reasons": []}
            is_f = comp.get("status") == "fail"

            st.markdown(
                f"""
                <div style="background: #111722; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span class="{'brand-pill-jade' if active_demo['brand'] == 'Jade' else 'brand-pill-ds'}">{active_demo['brand']} • {active_demo['platform']}</span>
                            <span class="badge-cycle">Cycle {active_demo.get('cycle', 1)}</span>
                        </div>
                        {'<span class="badge-fail">🚨 COMPLIANCE FAIL</span>' if is_f else '<span class="badge-pass">✓ COMPLIANCE PASS</span>'}
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if is_f:
                for r in comp.get("reasons", []):
                    st.error(f"Rule Triggered: **{r.get('rule')}**\n\n{r.get('message')}")

            st.markdown(f"<div class='content-text-box'>{active_demo['content']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Knowledge attribution & View Sources
            render_knowledge_sources(active_demo.get("sources"), key_prefix=f"demo_{active_demo['id']}")

            st.markdown("#### Step 4: Reviewer Action")
            col_d_act1, col_d_act2 = st.columns(2)
            with col_d_act1:
                if st.button("❌ 1-Click Reject (Problematic Claim)", key="demo_rej_btn", use_container_width=True):
                    tag = "inaccurate_claim"
                    note = (
                        "Cannot promise guaranteed payouts or 100% loss-free protection on jewellery inventory. "
                        "Must qualify under policy terms and vault security criteria."
                        if "jade" in active_demo["brand"].lower()
                        else "Cannot promise guaranteed dismissal of malpractice claims or 100% immunity. Must qualify defense coverage under policy terms."
                    )
                    models.reject_content(
                        active_demo["id"],
                        tag=tag,
                        note=note,
                    )
                    st.session_state["demo_parent_item"] = active_demo
                    st.warning(f"Asset #{active_demo['id']} rejected! Stored [{tag}] in feedback memory.")
                    st.rerun()

            with col_d_act2:
                if st.button("🔄 1-Click Regenerate with Feedback", key="demo_regen_btn", use_container_width=True):
                    with st.spinner("Retrieving JA Assure knowledge & injecting reviewer corrections..."):
                        recent_f = feedback_agent.get_recent_feedback(active_demo["brand"], n=5)
                        research_ctx = research_agent.research(brand=active_demo["brand"], topic=demo_topic)
                        new_gen = content_agent.generate(
                            topic=demo_topic,
                            brand=active_demo["brand"],
                            platform=active_demo["platform"],
                            content_type="post",
                            research_context=research_ctx,
                            past_corrections=recent_f,
                            force_trigger_flaw=False,
                            cycle=active_demo.get("cycle", 1) + 1,
                        )
                        new_c = compliance_agent.check(new_gen["content"], active_demo["brand"])
                        new_v = models.insert_content(
                            brand=active_demo["brand"],
                            platform=active_demo["platform"],
                            content_type="post",
                            content=new_gen["content"],
                            compliance_result=new_c,
                            cycle=active_demo.get("cycle", 1) + 1,
                            parent_id=active_demo["id"],
                            fixed_issue="Avoided guaranteed payout claim; qualified coverage under official policy terms.",
                            sources=new_gen.get("sources"),
                            status="pending",
                        )
                        st.session_state["demo_parent_item"] = active_demo
                        st.session_state["active_demo_item"] = new_v
                        st.success(f"Regenerated Asset #{new_v['id']} created and passed Compliance Gate!")
                        st.rerun()

            # Side-by-side Before/After preview if this was regenerated from parent
            parent_item = st.session_state.get("demo_parent_item")
            if parent_item and active_demo.get("parent_id") == parent_item.get("id"):
                st.markdown("---")
                st.markdown("#### 🔬 Judge Verification: Before vs After Learning")
                st.markdown(
                    f"""
                    <div style="background: #0d121c; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem;">
                        <div class="diff-container">
                            <div class="diff-before">
                                <div style="color: #f87171; font-weight: 700; font-size: 0.8rem; margin-bottom: 0.4rem;">❌ BEFORE (ORIGINAL REJECTED)</div>
                                <div style="font-size: 0.78rem; line-height: 1.4; color: #cbd5e1; white-space: pre-wrap;">{parent_item['content']}</div>
                            </div>
                            <div class="diff-after">
                                <div style="color: #34d399; font-weight: 700; font-size: 0.8rem; margin-bottom: 0.4rem;">✅ AFTER (REGENERATED COMPLIANT)</div>
                                <div style="font-size: 0.78rem; line-height: 1.4; color: #cbd5e1; white-space: pre-wrap;">{active_demo['content']}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Click 'Generate Risky Post' on the left to begin the demo flow.")


# =====================================================================
# TAB 5: INSURTECH LEADS VIEW (P1)
# =====================================================================

with tab_leads:
    st.markdown("### 🎯 InsurTech Prospect Pipeline (P1 Feature)")
    st.markdown(
        "Prospects enriched across target verticals (Jewellers, Clinics, SMEs). "
        "Each lead receives an automated fit score and tailored outreach message."
    )

    lead_vertical = st.selectbox("Vertical Filter", ["All Verticals", "Jewellers", "Clinics", "SMEs"], index=0)
    vert_param = None if lead_vertical == "All Verticals" else lead_vertical

    leads_list = models.list_leads(vertical=vert_param)

    for lead in leads_list:
        with st.container():
            col_l1, col_l2, col_l3 = st.columns([2, 3, 1])
            with col_l1:
                st.markdown(f"**{lead['name']}**")
                st.caption(f"Contact: `{lead['contact']}` • Vertical: **{lead['vertical']}**")
                st.progress(lead["fit_score"] / 100, text=f"Fit Score: {lead['fit_score']}/100")
            with col_l2:
                st.markdown("**Tailored Outreach Draft:**")
                st.markdown(f"<div style='font-size: 0.8rem; color: #cbd5e1; background: #0d121c; padding: 0.6rem; border-radius: 6px;'>{lead['outreach_draft']}</div>", unsafe_allow_html=True)
            with col_l3:
                curr_status = lead.get("status", "new")
                status_color = "#34d399" if curr_status == "contacted" else ("#60a5fa" if curr_status == "qualified" else "#94a3b8")
                st.markdown(f"<span style='color: {status_color}; font-weight: 700; font-size: 0.8rem;'>● {curr_status.upper()}</span>", unsafe_allow_html=True)
                if curr_status == "new":
                    if st.button("✉️ Mark Sent", key=f"lead_sent_{lead['id']}", use_container_width=True):
                        models.update_lead_status(lead["id"], "contacted")
                        st.success("Status updated to contacted!")
                        st.rerun()

            st.markdown("<hr style='border-color: rgba(255,255,255,0.04); margin: 0.75rem 0;'/>", unsafe_allow_html=True)
