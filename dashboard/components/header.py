"""
Enterprise Top Application Header Component for JA Assure.
Renders clean white top bar matching the reference design.
"""

import streamlit as st


def render_header() -> str:
    """
    Renders the clean white top application header:
    - Product title & mission tagline
    - Universal search input with ⌘K badge
    - Notification icon with indicator dot
    - Santosh (Marketing Team) user profile avatar
    """
    col_h_left, col_h_right = st.columns([1.6, 1.4])

    with col_h_left:
        st.markdown(
            """
            <div class="header-title-box">
                <div class="header-main-title">AI Marketing & Compliance Platform</div>
                <div class="header-main-sub">Intelligent content. Compliant always. Built for a safer tomorrow.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_h_right:
        c_search, c_notif, c_user = st.columns([3, 0.5, 2])
        
        with c_search:
            search_val = st.text_input(
                "Search",
                value=st.session_state.get("search_query", ""),
                placeholder="🔍 Search content, topics, or resources...   ⌘K",
                label_visibility="collapsed",
                key="top_search_input",
            )
            if search_val != st.session_state.get("search_query", ""):
                st.session_state["search_query"] = search_val

        with c_notif:
            st.markdown(
                """
                <div style="display: flex; align-items: center; justify-content: center; height: 38px; position: relative; cursor: pointer;">
                    <span style="font-size: 1.15rem; color: #475569;">🔔</span>
                    <span style="position: absolute; top: 6px; right: 4px; width: 7px; height: 7px; background: #DC2626; border-radius: 50%;"></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_user:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 0.6rem; height: 38px;">
                    <div class="user-avatar-circle">SA</div>
                    <div>
                        <div style="font-size: 0.82rem; font-weight: 700; color: #0F172A; line-height: 1.1;">Santosh <span style="font-size: 0.65rem; color: #64748B;">▼</span></div>
                        <div style="font-size: 0.68rem; color: #64748B;">Marketing Team</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom: 0.85rem;'></div>", unsafe_allow_html=True)
    return st.session_state.get("search_query", "")
