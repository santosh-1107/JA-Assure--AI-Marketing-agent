"""
JA Assure — AI Marketing & Compliance Platform
Enterprise InsurTech Product Workspace.
Intelligent content. Compliant always. Built for a safer tomorrow.
"""

import sys
import yaml
from pathlib import Path
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db
from backend.gemini_service import gemini_service
from backend.agents.content_agent import content_agent
from backend.agents.compliance_agent import compliance_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from backend.knowledge.ja_assure_sources import load_all_sources
from backend import models

from dashboard.components import (
    ENTERPRISE_CSS,
    render_sidebar,
    render_header,
    render_product_panels,
    render_metric_strip,
    render_review_card,
    render_review_detail_workspace,
    render_knowledge_right_widget,
    render_knowledge_library_page,
    render_feedback_right_widget,
    render_feedback_learning_page,
    render_analytics_page,
)

# Page configuration
st.set_page_config(
    page_title="JA Assure — AI Marketing & Compliance Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Enterprise CSS
st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)

# Initialize database schema if not present
init_db()

# State Management
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Home"
if "selected_brand_filter" not in st.session_state:
    st.session_state["selected_brand_filter"] = "All Brands"
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""
if "gen_brand" not in st.session_state:
    st.session_state["gen_brand"] = "Jade"

# Real database queries
pending_items_all = models.list_pending_content()
approved_items_all = models.list_approved_content()
feedback_items_all = models.list_all_feedback()
stats_data = feedback_agent.get_rejection_rate_analytics()
latest_cycle_rate = stats_data["cycles"][-1]["rejection_rate"] if stats_data.get("cycles") else 20.0
knowledge_sources_all = load_all_sources()

# 1. Enterprise Sidebar Navigation
active_page = render_sidebar(pending_count=len(pending_items_all))

# 2. Top Application Header
search_term = render_header()


# =====================================================================
# VIEW 1: HOME (PRODUCT WORKSPACE)
# =====================================================================

if active_page == "Home":
    # 2-Column Split Layout matching Reference Image
    col_main, col_rail = st.columns([2.55, 1.0])

    with col_main:
        # A. Dual Product Panels (JADE & DOCTORSHIELD)
        render_product_panels()

        # B. 5-Card Operational Metric Strip
        render_metric_strip(
            pending_count=len(pending_items_all),
            approved_count=len(approved_items_all),
            latest_rejection_rate=latest_cycle_rate,
            feedback_count=len(feedback_items_all),
            knowledge_count=len(knowledge_sources_all),
        )

        # C. Content Awaiting Human Review Workspace
        st.markdown(
            """
            <div class="workspace-section-header">
                <div class="section-title-with-bar">
                    <div class="section-bar"></div>
                    <div class="section-title-text">Content Awaiting Human Review</div>
                    <div class="section-sub-text">AI-generated marketing content must pass compliance review before publishing.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick Filter Row
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1:
            q_brand = st.selectbox("Brand", ["All Brands", "Jade", "DoctorShield"], index=0, label_visibility="collapsed", key="home_f_brand")
        with cf2:
            q_plat = st.selectbox("Platform", ["All Platforms", "LinkedIn", "Instagram", "X"], index=0, label_visibility="collapsed", key="home_f_plat")
        with cf3:
            q_status = st.selectbox("Status", ["All Status", "Fail Only", "Pass Only"], index=0, label_visibility="collapsed", key="home_f_status")
        with cf4:
            q_sort = st.selectbox("Sort", ["Newest First", "Compliance Risk", "Brand"], index=0, label_visibility="collapsed", key="home_f_sort")

        # Filter items for Home workspace preview
        b_arg = None if q_brand == "All Brands" else q_brand
        home_items = models.list_pending_content(brand=b_arg)

        filtered_home_items = []
        for item in home_items:
            if q_plat != "All Platforms" and item.get("platform") != q_plat:
                continue
            comp = item.get("compliance_result") or {"status": "pass", "reasons": []}
            is_f = (comp.get("status") == "fail")
            if q_status == "Fail Only" and not is_f:
                continue
            if q_status == "Pass Only" and is_f:
                continue
            if search_term and search_term.strip():
                st_clean = search_term.lower().strip()
                item_text = (item.get("content", "") + " " + item.get("brand", "") + " " + item.get("platform", "")).lower()
                if st_clean not in item_text:
                    continue
            filtered_home_items.append(item)

        if not filtered_home_items:
            st.info("No content currently awaiting review matching active filters.")
        else:
            for item in filtered_home_items[:5]:
                render_review_card(item, key_prefix="home")

    with col_rail:
        # A. Quote Card
        st.markdown(
            """
            <div class="right-widget-card" style="border-left: 3px solid #D4AF37;">
                <div class="quote-box">
                    “Enabling a safer, more resilient tomorrow through specialist insurance solutions.”
                </div>
                <div style="font-size: 0.82rem; font-weight: 800; color: #0F172A; margin-top: 0.5rem;">JA Assure</div>
                <div style="font-size: 0.70rem; color: #64748B;">Beyond Risk. To A Brighter Tomorrow.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # B. JA Assure Knowledge Widget
        render_knowledge_right_widget()

        # C. Recent Feedback Widget
        render_feedback_right_widget()


# =====================================================================
# VIEW 2: CONTENT STUDIO (GENERATE CONTENT)
# =====================================================================

elif active_page == "Generate Content":
    st.markdown("### Content Studio")
    st.caption("Step-by-step compliant marketing asset production workflow grounded in JA Assure knowledge.")

    col_studio_left, col_studio_right = st.columns([1.6, 1.4])

    with col_studio_left:
        st.markdown("##### 1. Production Parameters")
        
        # Step 1: Select Brand
        brand_idx = 0 if st.session_state.get("gen_brand") == "Jade" else 1
        c_brand = st.selectbox("Select Brand", ["Jade", "DoctorShield"], index=brand_idx, key="studio_brand")
        st.session_state["gen_brand"] = c_brand

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            c_platform = st.selectbox("Select Platform", ["LinkedIn", "Instagram", "X"], index=0, key="studio_plat")
        with col_p2:
            c_type = st.selectbox("Content Type", ["post", "carousel", "video_script"], index=0, key="studio_type")

        default_topic = (
            "Specialist Jewellers Block and Specie protection for jewellery businesses and luxury watch dealers"
            if c_brand == "Jade"
            else "Medical indemnity, malpractice litigation defense financing, and patient safety governance"
        )
        c_topic = st.text_area("Campaign Topic / Brief", value=default_topic, height=85, key=f"studio_topic_{c_brand}")

        force_trigger = st.checkbox("Simulate Non-Compliant Claim (For Compliance Testing)", value=False)
        btn_gen = st.button("Generate Draft Asset →", type="primary", use_container_width=True)

    with col_studio_right:
        st.markdown("##### 2. Retrieved JA Assure Knowledge Context")
        res_ctx = research_agent.research(brand=c_brand, topic=c_topic)
        retrieved_sources = res_ctx.get("sources", [])

        if retrieved_sources:
            for s in retrieved_sources:
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid {'#D4AF37' if c_brand == 'Jade' else '#0D9488'}; border-radius: 6px; padding: 0.85rem; margin-bottom: 0.65rem;">
                        <div style="font-size: 0.85rem; font-weight: 800; color: #0F172A;">{s.get('title')}</div>
                        <div style="font-size: 0.74rem; color: #475569; margin: 0.25rem 0;">{s.get('snippet', '')}</div>
                        <div style="font-size: 0.70rem; color: #2563EB;">Official Source: <a href="{s.get('url')}" target="_blank">{s.get('url')}</a></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Active Feedback Memory
        brand_fb = feedback_agent.get_recent_feedback(brand=c_brand, n=3)
        if brand_fb:
            st.markdown("##### Active Few-Shot Learned Constraints")
            for fb in brand_fb:
                st.markdown(
                    f"""
                    <div style="background: #FEF3C7; border: 1px solid #FDE68A; border-radius: 6px; padding: 0.45rem 0.65rem; margin-bottom: 0.35rem; font-size: 0.74rem; color: #92400E;">
                        <b>[{fb['tag']}]</b> {fb['note']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if btn_gen:
        with st.spinner("Generating marketing copy & verifying compliance..."):
            past_fb = feedback_agent.get_recent_feedback(brand=c_brand, n=5)
            gen_res = content_agent.generate(
                topic=c_topic,
                brand=c_brand,
                platform=c_platform,
                content_type=c_type,
                research_context=res_ctx,
                past_corrections=past_fb,
                force_trigger_flaw=force_trigger,
                cycle=1 if force_trigger else 2,
            )
            comp_res = compliance_agent.check(gen_res["content"], c_brand)
            saved = models.insert_content(
                brand=c_brand,
                platform=c_platform,
                content_type=c_type,
                content=gen_res["content"],
                compliance_result=comp_res,
                cycle=1 if force_trigger else 2,
                sources=gen_res.get("sources"),
                status="pending",
            )
            st.session_state["studio_last_asset"] = saved
            st.toast(f"Asset #{saved['id']} created and grounded in JA Assure knowledge!")

    last_studio = st.session_state.get("studio_last_asset")
    if last_studio:
        st.markdown("---")
        st.markdown("#### Draft Preview & Compliance Verification")
        render_review_card(last_studio, key_prefix="studio_out")


# =====================================================================
# VIEW 3: REVIEW QUEUE
# =====================================================================

elif active_page == "Review Queue":
    st.markdown("### Review Queue")
    st.caption("AI-generated marketing assets requiring human compliance approval.")

    # Filter Bar
    rf1, rf2, rf3, rf4 = st.columns(4)
    with rf1:
        f_b = st.selectbox("Filter Brand", ["All Brands", "Jade", "DoctorShield"], index=0, key="rq_view_brand")
    with rf2:
        f_p = st.selectbox("Filter Platform", ["All Platforms", "LinkedIn", "Instagram", "X"], index=0, key="rq_view_plat")
    with rf3:
        f_s = st.selectbox("Compliance Status", ["All Status", "Fail Only", "Pass Only"], index=0, key="rq_view_stat")
    with rf4:
        f_sort = st.selectbox("Sort Order", ["Newest First", "Compliance Risk", "Brand"], index=0, key="rq_view_sort")

    b_param = None if f_b == "All Brands" else f_b
    raw_list = models.list_pending_content(brand=b_param)

    filtered_list = []
    for it in raw_list:
        if f_p != "All Platforms" and it.get("platform") != f_p:
            continue
        c_res = it.get("compliance_result") or {"status": "pass", "reasons": []}
        is_fail = (c_res.get("status") == "fail")
        if f_s == "Fail Only" and not is_fail:
            continue
        if f_s == "Pass Only" and is_fail:
            continue
        if search_term and search_term.strip():
            term = search_term.lower().strip()
            text = (it.get("content", "") + " " + it.get("brand", "") + " " + it.get("platform", "")).lower()
            if term not in text:
                continue
        filtered_list.append(it)

    if f_sort == "Newest First":
        filtered_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif f_sort == "Brand":
        filtered_list.sort(key=lambda x: x.get("brand", ""))

    st.markdown(f"<div style='font-size: 0.80rem; color: #64748B; margin-bottom: 0.75rem;'>Showing <b>{len(filtered_list)}</b> items awaiting human review</div>", unsafe_allow_html=True)

    if not filtered_list:
        st.info("No content awaiting review matching your criteria.")
    else:
        for it in filtered_list:
            render_review_card(it, key_prefix="queue_view")


# =====================================================================
# VIEW 4: FEEDBACK & LEARNING
# =====================================================================

elif active_page == "Feedback & Learning":
    render_feedback_learning_page()


# =====================================================================
# VIEW 5: KNOWLEDGE LIBRARY
# =====================================================================

elif active_page == "Knowledge Library":
    render_knowledge_library_page()


# =====================================================================
# VIEW 6: JA ASSURE RESOURCES
# =====================================================================

elif active_page == "JA Assure Resources":
    st.markdown("### JA Assure Corporate & Underwriting Resources")
    st.caption("Official company literature, Lloyd's coverholder agreements, and regional syndicate underwriting principles.")

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem;">
                <div style="font-size: 1.05rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;">Corporate Profile & MGA Structure</div>
                <div style="font-size: 0.82rem; color: #475569; line-height: 1.55;">
                    JA Assure is an InsurTech Managing General Agent (MGA) operating across Southeast Asia with headquarters in Singapore. The firm combines deep underwriting expertise in high-risk specialty classes with bespoke digital binding technology.
                </div>
                <div style="margin-top: 1rem; font-size: 0.80rem; color: #334155;">
                    • <b>Delegated Authority:</b> Underwrites on behalf of Lloyd's of London syndicates.<br/>
                    • <b>Specialty Product Lines:</b> Jewellers Block & Specie (Jade) and Medical Indemnity (DoctorShield).<br/>
                    • <b>Regulatory Governance:</b> Adheres strictly to MAS and regional medical council advertising codes.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_res2:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem;">
                <div style="font-size: 1.05rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;">Official Reference Links</div>
                <div style="font-size: 0.82rem; color: #475569; line-height: 1.55;">
                    Direct links to authentic corporate knowledge and product literature:
                </div>
                <div style="margin-top: 0.85rem; font-size: 0.82rem; line-height: 1.8;">
                    • <a href="https://www.ja-assure.com" target="_blank" style="color: #2563EB;">JA Assure Corporate Homepage</a><br/>
                    • <a href="https://www.ja-assure.com/resources.html" target="_blank" style="color: #2563EB;">Official Knowledge Resources & Articles</a><br/>
                    • <a href="https://www.ja-assure.com/blog-jewellers-block.html" target="_blank" style="color: #D4AF37;">Jade Jewellers Block Specifications</a><br/>
                    • <a href="https://www.ja-assure.com/blog-medical-malpractice.html" target="_blank" style="color: #0D9488;">DoctorShield Medical Indemnity Governance</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =====================================================================
# VIEW 7: LEADS & OUTREACH
# =====================================================================

elif active_page == "Leads & Outreach":
    st.markdown("### Leads & Outreach")
    st.caption("Prospects enriched across target verticals (Clinics, Jewellers, SMEs) with fit scores and bespoke outreach drafts.")

    vert_choice = st.selectbox("Vertical Filter", ["All Verticals", "Jewellers", "Clinics", "SMEs"], index=0)
    vert_filter = None if vert_choice == "All Verticals" else vert_choice

    leads = models.list_leads(vertical=vert_filter)

    for l in leads:
        with st.container():
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.85rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                """,
                unsafe_allow_html=True,
            )
            col_ld1, col_ld2, col_ld3 = st.columns([1.8, 2.8, 1.2])
            with col_ld1:
                st.markdown(f"**{l['name']}**")
                st.caption(f"Contact: `{l['contact']}` • Line: **{l['vertical']}**")
                st.progress(l["fit_score"] / 100, text=f"Fit Score: {l['fit_score']}/100")
            with col_ld2:
                st.markdown("**Tailored Outreach Draft:**")
                st.markdown(f"<div style='font-size: 0.80rem; color: #334155; background: #F8FAFC; padding: 0.65rem; border-radius: 6px; border: 1px solid #E2E8F0;'>{l['outreach_draft']}</div>", unsafe_allow_html=True)
            with col_ld3:
                status = l.get("status", "new")
                status_color = "#059669" if status == "contacted" else ("#2563EB" if status == "qualified" else "#64748B")
                st.markdown(f"<div style='color: {status_color}; font-weight: 800; font-size: 0.78rem; text-transform: uppercase; margin-bottom: 0.4rem;'>● {status}</div>", unsafe_allow_html=True)
                if status == "new":
                    if st.button("Mark Contacted", key=f"lead_btn_{l['id']}", use_container_width=True):
                        models.update_lead_status(l["id"], "contacted")
                        st.toast("Status updated to contacted!")
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# VIEW 8: ANALYTICS
# =====================================================================

elif active_page == "Analytics":
    render_analytics_page()


# =====================================================================
# VIEW 9: BRAND GUIDELINES
# =====================================================================

elif active_page == "Brand Guidelines":
    st.markdown("### Official Brand Guidelines")
    st.caption("Authentic brand voice, approved vocabulary, restricted terminology, and platform framing from configuration prompts.")

    jade_prompt_file = PROJECT_ROOT / "prompts" / "jade.yaml"
    ds_prompt_file = PROJECT_ROOT / "prompts" / "doctorshield.yaml"

    col_bg_j, col_bg_ds = st.columns(2)

    with col_bg_j:
        if jade_prompt_file.exists():
            with open(jade_prompt_file, "r", encoding="utf-8") as f:
                jade_guide = yaml.safe_load(f)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #D4AF37; border-radius: 8px; padding: 1.25rem;">
                    <div style="font-size: 1.15rem; font-weight: 800; color: #D4AF37; margin-bottom: 0.5rem;">JADE</div>
                    <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 0.75rem;">{jade_guide.get('vertical')}</div>
                    <div style="font-size: 0.82rem; color: #1E293B; line-height: 1.5; margin-bottom: 0.75rem;">
                        <b>Persona & Tone:</b> {jade_guide.get('brand_voice', {}).get('persona')}<br/>
                        <b>Tone Attributes:</b> {jade_guide.get('brand_voice', {}).get('tone')}
                    </div>
                    <div style="font-size: 0.80rem; color: #15803D; margin-bottom: 0.5rem;">
                        <b>✔ Approved Vocabulary Preferences:</b>
                        <div>{", ".join(jade_guide.get('brand_voice', {}).get('vocabulary_preferences', []))}</div>
                    </div>
                    <div style="font-size: 0.80rem; color: #B91C1C; margin-bottom: 0.75rem;">
                        <b>✕ Restricted Prohibited Terminology:</b>
                        <div>{", ".join(jade_guide.get('brand_voice', {}).get('vocabulary_prohibitions', []))}</div>
                    </div>
                    <div style="font-size: 0.76rem; color: #475569; background: #FEF3C7; padding: 0.65rem; border-radius: 4px;">
                        <b>Compliant Framing Example:</b> "{jade_guide.get('sample_compliant_framing')}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_bg_ds:
        if ds_prompt_file.exists():
            with open(ds_prompt_file, "r", encoding="utf-8") as f:
                ds_guide = yaml.safe_load(f)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #0D9488; border-radius: 8px; padding: 1.25rem;">
                    <div style="font-size: 1.15rem; font-weight: 800; color: #0D9488; margin-bottom: 0.5rem;">DOCTORSHIELD</div>
                    <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 0.75rem;">{ds_guide.get('vertical')}</div>
                    <div style="font-size: 0.82rem; color: #1E293B; line-height: 1.5; margin-bottom: 0.75rem;">
                        <b>Persona & Tone:</b> {ds_guide.get('brand_voice', {}).get('persona')}<br/>
                        <b>Tone Attributes:</b> {ds_guide.get('brand_voice', {}).get('tone')}
                    </div>
                    <div style="font-size: 0.80rem; color: #15803D; margin-bottom: 0.5rem;">
                        <b>✔ Approved Vocabulary Preferences:</b>
                        <div>{", ".join(ds_guide.get('brand_voice', {}).get('vocabulary_preferences', []))}</div>
                    </div>
                    <div style="font-size: 0.80rem; color: #B91C1C; margin-bottom: 0.75rem;">
                        <b>✕ Restricted Prohibited Terminology:</b>
                        <div>{", ".join(ds_guide.get('brand_voice', {}).get('vocabulary_prohibitions', []))}</div>
                    </div>
                    <div style="font-size: 0.76rem; color: #475569; background: #CCFBF1; padding: 0.65rem; border-radius: 4px;">
                        <b>Compliant Framing Example:</b> "{ds_guide.get('sample_compliant_framing')}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =====================================================================
# VIEW 10: SETTINGS & SYSTEM STATUS
# =====================================================================

elif active_page == "Settings":
    st.markdown("### Settings & System Status")
    st.caption("Operational configuration, Lloyd's coverholder governance, and database diagnostic tools.")

    col_set1, col_set2 = st.columns(2)
    with col_set1:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem;">
                <div style="font-size: 0.95rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;">Operational Governance Hard Rules</div>
                <div style="font-size: 0.80rem; color: #475569; line-height: 1.6;">
                    1. <b>Zero Automated Publishing:</b> Every generated asset requires explicit human sign-off before entering the approved queue.<br/>
                    2. <b>Regulatory Claim Gate:</b> Guaranteed payout or 100% loss-free language is strictly blocked at the compliance gate.<br/>
                    3. <b>Knowledge Grounding Mandate:</b> Content must be anchored in verified facts from official JA Assure knowledge files.<br/>
                    4. <b>Audit Trail Immutability:</b> All reviewer rejections and edit rationales are permanently retained in SQLite.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_set2:
        llm_status = gemini_service.check_health()
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem;">
                <div style="font-size: 0.95rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;">System Engine Status</div>
                <div style="font-size: 0.80rem; color: #475569; line-height: 1.6;">
                    • <b>Engine Status:</b> {'Live Gemini Studio' if llm_status['is_live'] else 'Deterministic InsurTech Engine'}<br/>
                    • <b>Active Model:</b> {llm_status.get('model', 'Deterministic Rule Base')}<br/>
                    • <b>Storage:</b> SQLite Local Database<br/>
                    • <b>Knowledge Base:</b> 5 Verified JSON Documents<br/>
                    • <b>Operating Region:</b> Singapore (HQ) & Southeast Asia
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### Database Maintenance")
    if st.button("🔄 Reset & Re-Seed Demo Benchmark Dataset", type="secondary"):
        from scripts.seed_demo import seed_data
        seed_data()
        st.toast("Database restored to baseline 4-cycle benchmark (80% -> 20%)!")
        st.rerun()
