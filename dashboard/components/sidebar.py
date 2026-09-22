"""
Enterprise Sidebar Component for JA Assure AI Marketing & Compliance Platform.
Renders persistent dark navy navigation bar matching the reference design.
"""

import streamlit as st


def render_sidebar(pending_count: int = 0) -> str:
    """
    Renders enterprise left sidebar with:
    - JA Assure gold petal emblem and brand wordmark
    - Clean line-icon navigation with active gold border indicator
    - Dynamic review count badge and 'New' badge
    - Operating region and Southeast Asia flags
    """
    with st.sidebar:
        # Top Brand Logo
        st.markdown(
            """
            <div class="sidebar-brand-wrapper">
                <div class="sidebar-brand-row">
                    <svg class="brand-logo-petals" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M50 8 C38 28 32 45 32 60 C32 78 40 88 50 88 C60 88 68 78 68 60 C68 45 62 28 50 8 Z" fill="#D4AF37"/>
                        <path d="M30 30 C18 45 15 58 15 70 C15 82 22 90 32 90 C40 90 45 84 45 72 C45 58 38 42 30 30 Z" fill="#E5C07B" opacity="0.85"/>
                        <path d="M70 30 C82 45 85 58 85 70 C85 82 78 90 68 90 C60 90 55 84 55 72 C55 58 62 42 70 30 Z" fill="#B89628" opacity="0.85"/>
                    </svg>
                    <div>
                        <div class="brand-logo-text">JA Assure</div>
                        <div class="brand-logo-tagline">Beyond Risk. To A Brighter Tomorrow.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Active page tracking
        current_page = st.session_state.get("active_page", "Home")

        nav_items = [
            ("Home", "🏠 Home"),
            ("Generate Content", "✏️ Generate Content"),
            ("Review Queue", f"📋 Review Queue  ({pending_count})" if pending_count > 0 else "📋 Review Queue"),
            ("Feedback & Learning", "💬 Feedback & Learning"),
            ("Knowledge Library", "📖 Knowledge Library"),
            ("JA Assure Resources", "📰 JA Assure Resources"),
            ("Leads & Outreach", "👥 Leads & Outreach  [New]"),
            ("Analytics", "📊 Analytics"),
            ("Brand Guidelines", "🛡️ Brand Guidelines"),
            ("Settings", "⚙️ Settings"),
        ]

        for page_id, label in nav_items:
            is_active = (current_page == page_id)
            btn_type = "primary" if is_active else "secondary"

            # Render button
            if st.button(
                label,
                key=f"nav_{page_id}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state["active_page"] = page_id
                st.rerun()

        # Bottom Operating Region & Flags
        st.markdown(
            """
            <div class="sidebar-region-footer">
                <div class="region-label">Operating Region</div>
                <div class="region-pill">
                    <span>🌐 Singapore (SG)</span>
                    <span style="font-size: 0.65rem; color: #94A3B8;">▼</span>
                </div>
                <div style="font-size: 0.72rem; color: #CBD5E1; margin-top: 0.85rem; font-weight: 600;">
                    Trusted across Southeast Asia
                </div>
                <div class="flags-row">
                    <span>🇸🇬</span>
                    <span>🇲🇾</span>
                    <span>🇮🇩</span>
                    <span>🇹🇭</span>
                    <span>🇻🇳</span>
                </div>
                <div class="region-tagline">
                    Same commitment. A more resilient region.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.get("active_page", "Home")
