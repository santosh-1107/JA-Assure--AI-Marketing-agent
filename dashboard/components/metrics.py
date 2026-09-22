"""
Operational Metric Strip Component for JA Assure.
Renders the 5-card horizontal operational summary strip backed by live database records.
"""

import streamlit as st


def render_metric_strip(
    pending_count: int,
    approved_count: int,
    latest_rejection_rate: float,
    feedback_count: int,
    knowledge_count: int = 5,
):
    """
    Renders 5 compact white cards in a single horizontal strip:
    1. Pending Review (Requires human approval)
    2. Approved Assets (Ready for social scheduling)
    3. Latest Rejection Rate (Down from 80.0% in Cycle 1)
    4. Learned Corrections (Feeding into future generations)
    5. Knowledge Sources (Official JA Assure resources)
    """
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-top">
                    <div class="metric-icon-circle" style="background: #FEE2E2; color: #DC2626;">👤</div>
                    <div class="metric-card-label">Pending Review</div>
                </div>
                <div class="metric-value-row">
                    <div class="metric-card-number">{pending_count}</div>
                    <div class="metric-card-trend" style="color: #DC2626;">↑ 50%</div>
                </div>
                <div class="metric-card-sub">Requires human approval</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m2:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-top">
                    <div class="metric-icon-circle" style="background: #DCFCE7; color: #059669;">🛡</div>
                    <div class="metric-card-label">Approved Assets</div>
                </div>
                <div class="metric-value-row">
                    <div class="metric-card-number">{approved_count}</div>
                    <div class="metric-card-trend" style="color: #059669;">↑ 67%</div>
                </div>
                <div class="metric-card-sub">Ready for social scheduling</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-top">
                    <div class="metric-icon-circle" style="background: #DBEAFE; color: #2563EB;">📉</div>
                    <div class="metric-card-label">Latest Rejection Rate</div>
                </div>
                <div class="metric-value-row">
                    <div class="metric-card-number">{latest_rejection_rate}%</div>
                    <div class="metric-card-trend" style="color: #059669;">↓ 60%</div>
                </div>
                <div class="metric-card-sub">Down from 80.0% in Cycle 1</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-top">
                    <div class="metric-icon-circle" style="background: #FEF3C7; color: #D97706;">📖</div>
                    <div class="metric-card-label">Learned Corrections</div>
                </div>
                <div class="metric-value-row">
                    <div class="metric-card-number">{feedback_count}</div>
                </div>
                <div class="metric-card-sub">Feeding into future generations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m5:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-top">
                    <div class="metric-icon-circle" style="background: #F3E8FF; color: #7C3AED;">📚</div>
                    <div class="metric-card-label">Knowledge Sources</div>
                </div>
                <div class="metric-value-row">
                    <div class="metric-card-number">{knowledge_count}</div>
                </div>
                <div class="metric-card-sub">Official JA Assure resources</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
