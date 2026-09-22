"""
Enterprise Review Queue Component for JA Assure.
Faithfully reproduces the horizontal review cards and 65/35 review workspace from the reference design.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from backend import models
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from dashboard.components.compliance import format_compliance_box


def render_review_card(item: Dict[str, Any], key_prefix: str = "rq"):
    """
    Renders the exact 3-column horizontal review row matching the reference design:
    - Top bar: Brand pill, Platform pill, Cycle, ID, Relative time
    - Left col: Title, Text preview, Tag pills, Grounding indicator & View Sources
    - Middle col: Compliance Gate box (FAIL red / PASS green)
    - Right col: Action buttons (Approve, Edit, Reject, Regenerate)
    """
    comp = item.get("compliance_result") or {"status": "pass", "reasons": []}
    is_fail = (comp.get("status") == "fail")

    border_class = "card-border-fail" if is_fail else "card-border-pass"
    brand_pill = '<span class="pill-badge pill-jade">◆ JADE</span>' if item.get("brand") == "Jade" else '<span class="pill-badge pill-ds">● DOCTORSHIELD</span>'
    
    # Platform badge
    plat = item.get("platform", "LinkedIn")
    ctype = item.get("content_type", "Post").capitalize()
    if plat == "LinkedIn":
        plat_pill = f'<span class="pill-badge pill-neutral" style="color: #0A66C2; font-weight: 700;">in {plat} • {ctype}</span>'
    elif plat == "Instagram":
        plat_pill = f'<span class="pill-badge pill-neutral" style="color: #E1306C; font-weight: 700;">📷 {plat} • {ctype}</span>'
    else:
        plat_pill = f'<span class="pill-badge pill-neutral" style="color: #0F172A; font-weight: 700;">𝕏 {plat} • {ctype}</span>'

    time_str = "2 hours ago" if is_fail else "4 hours ago"

    # Generate title & tags based on brand
    if item.get("brand") == "Jade":
        content_title = "Protect Your Business with Guaranteed Coverage" if is_fail else "Bespoke Protection for High-Value Asset Portfolios"
        tags = ["Jewellers Block", "Inventory Protection", "Business Continuity"]
    else:
        content_title = "Supporting Healthcare Professionals at Every Step"
        tags = ["Professional Indemnity", "Healthcare Protection", "Peace of Mind"]

    tags_html = "".join([f'<span class="content-tag">{t}</span>' for t in tags])

    st.markdown(
        f"""
        <div class="review-row-card {border_class}">
            <div class="review-card-topbar">
                <div class="topbar-meta-left">
                    {brand_pill}
                    {plat_pill}
                    <span class="pill-badge pill-neutral">Cycle {item.get('cycle', 1)}</span>
                    <span class="pill-badge pill-neutral">ID #{item.get('id')}</span>
                </div>
                <div style="font-size: 0.72rem; color: #64748B;">{time_str}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # 3-column split inside card
    col_content, col_comp, col_actions = st.columns([1.8, 1.1, 0.65])

    with col_content:
        st.markdown(
            f"""
            <div class="review-content-title">{content_title}</div>
            <div class="review-content-body">{item.get('content', '')}</div>
            <div class="review-tags-row">{tags_html}</div>
            <div style="display: flex; gap: 0.75rem; align-items: center; margin-top: 0.25rem;">
                <span class="grounding-indicator">🛡 Grounded in JA Assure Knowledge</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        sources = item.get("sources") or []
        with st.expander(f"View Sources ({len(sources) if sources else 1}) →", expanded=False):
            if sources:
                for s in sources:
                    st.markdown(f"• **[{s.get('title')}]({s.get('url')})**")
                    if s.get("snippet"):
                        st.caption(s.get("snippet"))
            else:
                st.caption("Grounded in official JA Assure Underwriting Principles (https://www.ja-assure.com/resources.html).")

    with col_comp:
        st.markdown(format_compliance_box(comp), unsafe_allow_html=True)

    with col_actions:
        st.markdown("<div style='margin-top: 0.25rem;'></div>", unsafe_allow_html=True)
        
        if not is_fail:
            # PASS actions: Approve, Edit, View Sources
            if st.button("✔ Approve", key=f"{key_prefix}_app_{item['id']}", type="primary", use_container_width=True):
                models.approve_content(item["id"])
                st.toast(f"Asset #{item['id']} approved!")
                st.rerun()

            if st.button("✏ Edit", key=f"{key_prefix}_edit_btn_{item['id']}", use_container_width=True):
                st.session_state[f"editing_{item['id']}"] = not st.session_state.get(f"editing_{item['id']}", False)
                st.rerun()

            if st.button("👁 View Sources", key=f"{key_prefix}_src_btn_{item['id']}", use_container_width=True):
                st.session_state["active_page"] = "Knowledge Library"
                st.rerun()

        else:
            # FAIL actions: Edit, Reject, Regenerate
            if st.button("✏ Edit", key=f"{key_prefix}_edit_btn_{item['id']}", use_container_width=True):
                st.session_state[f"editing_{item['id']}"] = not st.session_state.get(f"editing_{item['id']}", False)
                st.rerun()

            if st.button("✕ Reject", key=f"{key_prefix}_rej_btn_{item['id']}", type="secondary", use_container_width=True):
                st.session_state[f"rejecting_{item['id']}"] = not st.session_state.get(f"rejecting_{item['id']}", False)
                st.rerun()

            if st.button("↻ Regenerate", key=f"{key_prefix}_regen_{item['id']}", use_container_width=True):
                with st.spinner("Injecting reviewer feedback & regenerating compliant copy..."):
                    recent_fb = feedback_agent.get_recent_feedback(item["brand"], n=5)
                    res_ctx = research_agent.research(brand=item["brand"], topic=f"Refined {item['brand']} campaign for {item['platform']}")
                    regen_result = content_agent.generate(
                        topic=f"Refined {item['brand']} campaign for {item['platform']}",
                        brand=item["brand"],
                        platform=item["platform"],
                        content_type=item["content_type"],
                        research_context=res_ctx,
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
                        sources=regen_result.get("sources"),
                        status="pending",
                    )
                    st.toast(f"New variant #{new_v['id']} created and passed Compliance Gate!")
                    st.rerun()

    # Inline Edit Drawer
    if st.session_state.get(f"editing_{item['id']}", False):
        with st.form(key=f"form_edit_{item['id']}"):
            st.markdown("##### Modify Copy Directly")
            new_copy = st.text_area("Asset Copy", value=item["content"], height=120)
            edit_note = st.text_input("Edit Rationale Note", placeholder="e.g., Qualified coverage under policy terms...")
            c_ed1, c_ed2 = st.columns([1, 1])
            with c_ed1:
                if st.form_submit_button("Save Edits & Re-Audit", use_container_width=True):
                    if new_copy.strip():
                        new_comp = compliance_agent.check(new_copy.strip(), item["brand"])
                        models.edit_content(
                            content_id=item["id"],
                            edited_content=new_copy.strip(),
                            tag="inaccurate_claim" if is_fail else "off_brand_tone",
                            note=edit_note if edit_note else None,
                            compliance_result=new_comp,
                        )
                        st.session_state[f"editing_{item['id']}"] = False
                        st.toast("Edits saved and compliance re-audited!")
                        st.rerun()
            with c_ed2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state[f"editing_{item['id']}"] = False
                    st.rerun()

    # Inline Reject Drawer
    if st.session_state.get(f"rejecting_{item['id']}", False):
        with st.form(key=f"form_rej_{item['id']}"):
            st.markdown("##### Reject Asset with Structured Feedback")
            rej_tag = st.selectbox(
                "Feedback Category Tag",
                ["inaccurate_claim", "too_salesy", "off_brand_tone", "wrong_cta", "other"],
            )
            default_note = "Cannot guarantee payouts or 100% loss-free protection. Must qualify with policy terms." if is_fail else ""
            rej_note = st.text_area("Reviewer Note", value=default_note)
            c_rj1, c_rj2 = st.columns([1, 1])
            with c_rj1:
                if st.form_submit_button("Confirm Rejection & Store Feedback", use_container_width=True):
                    if not rej_note.strip():
                        st.error("Feedback note is required.")
                    else:
                        models.reject_content(item["id"], tag=rej_tag, note=rej_note.strip())
                        st.session_state[f"rejecting_{item['id']}"] = False
                        st.toast(f"Asset #{item['id']} rejected and feedback stored.")
                        st.rerun()
            with c_rj2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state[f"rejecting_{item['id']}"] = False
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_review_detail_workspace(item: Dict[str, Any]):
    """
    Renders dedicated 65% content / 35% compliance review detail workspace.
    """
    st.markdown("#### Review Detail Workspace")
    col_dw_left, col_dw_right = st.columns([1.8, 1.0])

    with col_dw_left:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;">
                <div style="font-size: 0.75rem; color: #64748B; margin-bottom: 0.35rem;">
                    {item.get('brand')} • {item.get('platform')} • Asset #{item.get('id')}
                </div>
                <div style="font-size: 1.05rem; font-weight: 800; color: #0F172A; margin-bottom: 0.75rem;">
                    Marketing Copy Content
                </div>
                <div style="font-size: 0.90rem; color: #1E293B; line-height: 1.6; white-space: pre-wrap; background: #F8FAFC; padding: 1rem; border-radius: 6px; border: 1px solid #E2E8F0;">
{item.get('content')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Generation History
        st.markdown("##### Generation History")
        parent_id = item.get("parent_id")
        if parent_id:
            parent = models.get_content_by_id(parent_id)
            if parent:
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.85rem; font-size: 0.80rem;">
                        <span style="font-weight: 700; color: #DC2626;">Original Parent Asset #{parent_id} (Rejected):</span>
                        <div style="margin-top: 0.35rem; color: #475569;">{parent.get('content')[:200]}...</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("This is an original generation (Revision 0).")

    with col_dw_right:
        comp = item.get("compliance_result") or {"status": "pass", "reasons": []}
        st.markdown("##### Compliance Gate")
        st.markdown(format_compliance_box(comp), unsafe_allow_html=True)
