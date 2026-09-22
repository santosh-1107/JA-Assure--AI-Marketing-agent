"""
Enterprise InsurTech Component Renderers for JA Assure AI Marketing Agent.
Houses reusable UI components strictly adhering to enterprise design direction:
- Top Header with Universal Search & Santosh Profile
- Enterprise Left Sidebar with Badges & Regional Compliance Indicators
- Split Hero Panels for JADE & DOCTORSHIELD
- Real-time KPI Ribbon
- Split Review Cards with Prominent Compliance Gates
- 5-Step Judge Demonstration Timeline
- Official JA Assure Knowledge Attributions
"""

import streamlit as st
from typing import Any, Dict, List, Optional


def render_top_header() -> str:
    """
    Renders enterprise top header with:
    - Product title & mission subtitle
    - Notification icon & Santosh profile
    - Returns search query string from text input
    """
    col_hdr1, col_hdr2 = st.columns([3, 2])
    
    with col_hdr1:
        st.markdown(
            """
            <div class="top-header-left">
                <div class="top-header-title">
                    <span style="display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; background: #1e293b; border-radius: 6px; border: 1px solid rgba(255,255,255,0.15); font-size: 0.85rem; font-weight: 800; color: #38bdf8;">JA</span>
                    AI Marketing Agent
                    <span style="font-size: 0.72rem; font-weight: 600; color: #94a3b8; background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); padding: 0.15rem 0.5rem; border-radius: 4px; margin-left: 0.25rem;">ENTERPRISE INSURTECH</span>
                </div>
                <div class="top-header-subtitle">
                    Intelligent content. Compliant always. Built for a safer tomorrow.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_hdr2:
        col_search, col_profile = st.columns([2.5, 1.8])
        with col_search:
            search_query = st.text_input(
                "Search",
                value=st.session_state.get("search_query", ""),
                placeholder="Search content, topics, or resources...",
                label_visibility="collapsed",
                key="global_search_input",
            )
            if search_query != st.session_state.get("search_query", ""):
                st.session_state["search_query"] = search_query
        
        with col_profile:
            st.markdown(
                """
                <div class="user-profile-badge">
                    <div class="user-avatar">ST</div>
                    <div>
                        <div class="user-meta-name">Santosh</div>
                        <div class="user-meta-role">Marketing Team</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
    return search_query


def render_sidebar_nav(pending_count: int = 0) -> str:
    """
    Renders enterprise left sidebar navigation with dynamic review queue count badge,
    authentic brand switcher, and Southeast Asian operating region indicator.
    """
    with st.sidebar:
        # JA Assure Brand Header
        st.markdown(
            """
            <div class="sidebar-brand-container">
                <div class="sidebar-logo">
                    <div class="sidebar-logo-icon">JA</div>
                    <div>
                        <div class="sidebar-brand-title">JA Assure</div>
                        <div class="sidebar-brand-badge">InsurTech MGA Platform</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Brand Filter Selector
        st.markdown("<div class='nav-section-title'>Product Portfolio</div>", unsafe_allow_html=True)
        current_brand_filter = st.selectbox(
            "Filter by Brand",
            ["All Brands", "Jade", "DoctorShield"],
            index=["All Brands", "Jade", "DoctorShield"].index(st.session_state.get("selected_brand_filter", "All Brands")),
            label_visibility="collapsed",
            key="sb_brand_filter",
        )
        st.session_state["selected_brand_filter"] = current_brand_filter

        # Navigation Options
        st.markdown("<div class='nav-section-title'>Navigation</div>", unsafe_allow_html=True)
        
        nav_options = [
            ("Dashboard", "Dashboard"),
            ("Generate Content", "Generate Content"),
            ("Review Queue", f"Review Queue ({pending_count})" if pending_count > 0 else "Review Queue"),
            ("Feedback & Learning", "Feedback & Learning"),
            ("Knowledge Library", "Knowledge Library"),
            ("JA Assure Resources", "JA Assure Resources"),
            ("Judge Demonstration", "Judge Demonstration"),
            ("Leads Pipeline", "InsurTech Leads"),
            ("Analytics", "Analytics"),
            ("System Settings", "Settings"),
        ]

        active_page = st.session_state.get("active_page", "Dashboard")
        
        for key_name, label in nav_options:
            is_active = (active_page == key_name)
            btn_type = "primary" if is_active else "secondary"
            
            if st.button(
                label,
                key=f"nav_btn_{key_name}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state["active_page"] = key_name
                st.rerun()

        # Database Quick Seeder / Governance rule
        st.markdown("<div class='nav-section-title'>Operations & Governance</div>", unsafe_allow_html=True)
        if st.button("Reload Demo Seed Data", use_container_width=True):
            from scripts.seed_demo import seed_data
            seed_data()
            st.toast("Demo dataset re-seeded with 4 cycles (80% -> 20%)!")
            st.rerun()

        # Regional Trust & Compliance Footer
        st.markdown(
            """
            <div class="sidebar-region-box">
                <div class="sidebar-region-header">
                    <span>🇸🇬</span> Operating Region
                </div>
                <div class="sidebar-region-val">Singapore (HQ) & SE Asia</div>
                <div class="sidebar-region-sub">Lloyd's Coverholder & Syndicate Underwriting Compliance</div>
                <div style="margin-top: 0.5rem; font-size: 0.70rem; color: #10b981; font-weight: 600;">
                    ✓ Zero Automated Publishing
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.get("active_page", "Dashboard")


def render_hero_section():
    """
    Renders product-focused split hero area:
    - Left: JADE (Jewellers Block & Specie Insurance)
    - Right: DOCTORSHIELD (Medical Indemnity Insurance)
    """
    col_jade, col_ds = st.columns(2)

    with col_jade:
        st.markdown(
            """
            <div class="hero-panel hero-panel-jade">
                <div class="hero-brand-tag tag-jade">
                    <span>✦</span> JADE • Jewellers Block & Specie Insurance
                </div>
                <div class="hero-headline">
                    Specialist protection for jewellery businesses
                </div>
                <div class="hero-support-text">
                    Comprehensive commercial trade coverage for stock in trade, physical vaults, international transit, trade exhibitions, and private residence vaults. Grounded in official JA Assure knowledge.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate Jade Content", key="hero_btn_jade", use_container_width=True):
            st.session_state["active_page"] = "Generate Content"
            st.session_state["gen_brand"] = "Jade"
            st.rerun()

    with col_ds:
        st.markdown(
            """
            <div class="hero-panel hero-panel-ds">
                <div class="hero-brand-tag tag-ds">
                    <span>✚</span> DOCTORSHIELD • Medical Indemnity Insurance
                </div>
                <div class="hero-headline">
                    Professional protection for healthcare professionals
                </div>
                <div class="hero-support-text">
                    Specialized medico-legal defense litigation financing and patient safety governance for surgeons, specialists, and clinics. Adheres strictly to claims-made healthcare advertising standards.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate DoctorShield Content", key="hero_btn_ds", use_container_width=True):
            st.session_state["active_page"] = "Generate Content"
            st.session_state["gen_brand"] = "DoctorShield"
            st.rerun()

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)


def render_kpi_ribbon(
    pending_count: int,
    approved_count: int,
    latest_rejection_rate: float,
    feedback_count: int,
    knowledge_count: int = 5,
):
    """
    Renders compact 5-metric enterprise KPI row backed directly by live SQLite database records.
    """
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Pending Review</div>
                <div class="kpi-value" style="color: {'#f87171' if pending_count > 0 else '#f8fafc'};">{pending_count}</div>
                <div class="kpi-caption">Requires human approval</div>
                <span class="kpi-trend trend-{'crimson' if pending_count > 0 else 'emerald'}">
                    {'Action Required' if pending_count > 0 else 'Queue Clear'}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Approved Assets</div>
                <div class="kpi-value" style="color: #34d399;">{approved_count}</div>
                <div class="kpi-caption">Ready for social scheduling</div>
                <span class="kpi-trend trend-emerald">Verified Compliant</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Latest Rejection Rate</div>
                <div class="kpi-value" style="color: #60a5fa;">{latest_rejection_rate}%</div>
                <div class="kpi-caption">Down from 80.0% in Cycle 1</div>
                <span class="kpi-trend trend-gold">-75% Error Drop</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Learned Corrections</div>
                <div class="kpi-value" style="color: #e5c07b;">{feedback_count}</div>
                <div class="kpi-caption">Feeding into future prompts</div>
                <span class="kpi-trend trend-gold">Active Memory</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k5:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Knowledge Sources</div>
                <div class="kpi-value" style="color: #2dd4bf;">{knowledge_count}</div>
                <div class="kpi-caption">Official JA Assure documents</div>
                <span class="kpi-trend trend-teal">Verified MGA Grounding</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


def render_knowledge_sources(sources: Optional[List[Dict[str, Any]]], key_prefix: str = "src"):
    """
    Renders official JA Assure knowledge grounding badge and expandable source details.
    """
    if not sources:
        return

    with st.expander("View Verified Knowledge Sources", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.5rem;">
                Official grounding context retrieved from <a href="https://www.ja-assure.com/resources.html" target="_blank" style="color: #38bdf8;">JA Assure Resources</a>:
            </div>
            """,
            unsafe_allow_html=True,
        )
        for s in sources:
            title = s.get("title", "JA Assure Knowledge Resource")
            url = s.get("url", "https://www.ja-assure.com/resources.html")
            vertical = s.get("vertical", "")
            key_facts = s.get("key_facts", [])
            snippet = s.get("snippet", "")

            st.markdown(f"**Resource:** [{title}]({url})")
            if vertical:
                st.caption(f"Domain / Line: {vertical}")
            if key_facts:
                st.markdown("**Underwriting & Grounding Facts:**")
                for kf in key_facts[:3]:
                    st.markdown(f"- {kf}")
            elif snippet:
                st.markdown(f"*{snippet}*")
            st.markdown("---")


def render_demo_timeline(active_step: int = 1):
    """
    Renders the 5-step visual flow timeline for Judge Demonstration:
    01 Generate -> 02 Compliance -> 03 Human Review -> 04 Feedback -> 05 Regenerate
    """
    steps = [
        ("01", "Generate"),
        ("02", "Compliance Gate"),
        ("03", "Human Review"),
        ("04", "Store Feedback"),
        ("05", "Regenerate & Learn"),
    ]

    items_html = ""
    for idx, (num, label) in enumerate(steps, start=1):
        is_current = (idx == active_step)
        border_color = "#38bdf8" if is_current else "rgba(255,255,255,0.12)"
        bg_num = "rgba(56, 189, 248, 0.2)" if is_current else "#1e293b"
        color_label = "#ffffff" if is_current else "#94a3b8"

        items_html += f"""
        <div class="timeline-step-item">
            <div class="timeline-step-num" style="background: {bg_num}; border-color: {border_color}; color: {'#38bdf8' if is_current else '#ffffff'};">
                {num}
            </div>
            <div class="timeline-step-label" style="color: {color_label}; font-weight: {'800' if is_current else '600'};">
                {label}
            </div>
        </div>
        """
        if idx < len(steps):
            items_html += '<div class="timeline-step-arrow">→</div>'

    st.markdown(
        f"""
        <div class="demo-timeline">
            {items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
