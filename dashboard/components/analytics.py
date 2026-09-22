"""
Analytics Component for JA Assure.
Visualizes marketing production volume, compliance pass rates, and platform distributions.
"""

import pandas as pd
import streamlit as st
from backend import models


def render_analytics_page():
    """
    Renders enterprise analytics & Risk Intelligence workspace with real database queries.
    Features:
    - Operational throughput metrics
    - Interactive Risk Heatmap Matrix (Issue Types x Brands/Platforms)
    - Top Recurring Compliance Issues breakdown
    - Risk Level Distribution (LOW / MEDIUM / HIGH)
    - Brand & Platform production charts
    """
    st.markdown("### Risk Intelligence & Operational Analytics")
    st.caption("Database-driven monitoring of marketing throughput, compliance risk distributions, and recurring regulatory issues.")

    from backend.services.analytics_service import (
        get_risk_heatmap,
        get_top_recurring_issues,
        get_risk_distribution,
    )

    all_content = models.list_all_content()
    approved = models.list_approved_content()
    pending = models.list_pending_content()
    rejected = [c for c in all_content if c.get("status") == "rejected"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Generated Assets", len(all_content))
    with col2:
        st.metric("Approved Assets", len(approved))
    with col3:
        st.metric("Pending Review", len(pending))
    with col4:
        pass_rate = round(len(approved) / len(all_content) * 100, 1) if all_content else 0.0
        st.metric("Compliance Clearance", f"{pass_rate}%")

    st.markdown("---")

    # =========================================================================
    # RISK INTELLIGENCE & HEATMAP SECTION
    # =========================================================================
    st.markdown("#### 🛡️ Marketing Risk Heatmap Matrix")
    st.caption("Cross-dimensional risk concentration derived from live reviewer rejections and compliance gate evaluations.")

    col_toggle, col_legend = st.columns([1.5, 2.5])
    with col_toggle:
        group_mode = st.radio(
            "Matrix Columns:",
            ["Brand", "Platform"],
            horizontal=True,
            key="heatmap_group_radio",
        )
    with col_legend:
        st.markdown(
            """
            <div style="font-size: 0.76rem; color: #64748B; padding-top: 0.65rem; text-align: right;">
                <b>Severity Gradient:</b> 
                <span style="background: #FEF2F2; color: #DC2626; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700;">High Risk (3+)</span>
                <span style="background: #FFFBEB; color: #D97706; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700;">Moderate (1-2)</span>
                <span style="background: #F0FDF4; color: #16A34A; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700;">Clean (0)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Fetch live heatmap data
    g_param = "brand" if group_mode == "Brand" else "platform"
    heatmap_data = get_risk_heatmap(group_by=g_param)
    columns = heatmap_data.get("columns", [])
    rows = heatmap_data.get("rows", [])

    if rows:
        # Build HTML table for rich enterprise heatmap styling
        headers_html = "".join([f"<th style='padding: 8px 14px; text-align: center; border-bottom: 2px solid #CBD5E1; color: #1E293B;'>{col}</th>" for col in columns])
        rows_html = ""

        for r in rows:
            itype = r.get("issue_type", "").replace("_", " ").title()
            tot = r.get("total", 0)
            cells_html = ""
            for col in columns:
                val = r.get(col, 0)
                if val == 0:
                    bg = "#F8FAFC"
                    color = "#94A3B8"
                    weight = "normal"
                elif val <= 2:
                    bg = "#FEF3C7"
                    color = "#B45309"
                    weight = "bold"
                else:
                    bg = "#FEE2E2"
                    color = "#B91C1C"
                    weight = "bold"

                cells_html += f"<td style='padding: 8px 14px; text-align: center; background: {bg}; color: {color}; font-weight: {weight}; border-bottom: 1px solid #E2E8F0;'>{val}</td>"

            rows_html += f"""
            <tr>
                <td style='padding: 8px 14px; font-weight: 600; color: #0F172A; border-bottom: 1px solid #E2E8F0; background: #FFFFFF;'>{itype}</td>
                {cells_html}
                <td style='padding: 8px 14px; text-align: center; font-weight: 700; color: #0F172A; border-bottom: 1px solid #E2E8F0; background: #F1F5F9;'>{tot}</td>
            </tr>
            """

        table_html = f"""
        <table style='width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-bottom: 1.25rem; border-radius: 6px; overflow: hidden; border: 1px solid #CBD5E1;'>
            <thead style='background: #F1F5F9;'>
                <tr>
                    <th style='padding: 8px 14px; text-align: left; border-bottom: 2px solid #CBD5E1; color: #1E293B;'>Issue Category</th>
                    {headers_html}
                    <th style='padding: 8px 14px; text-align: center; border-bottom: 2px solid #CBD5E1; color: #1E293B;'>Total</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No compliance violations currently recorded in review history.")

    st.markdown("---")

    # =========================================================================
    # RECURRING VIOLATIONS & RISK DISTRIBUTION
    # =========================================================================
    col_rec, col_dist = st.columns([1.6, 1.4])

    with col_rec:
        st.markdown("#### Top Recurring Violations")
        top_issues = get_top_recurring_issues(limit=5)
        if top_issues:
            for item in top_issues:
                issue_label = item.get("issue", "").replace("_", " ").title()
                freq = item.get("frequency", 0)
                pct = item.get("percentage", 0.0)
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 700; color: #0F172A; font-size: 0.85rem;">{issue_label}</div>
                            <div style="font-size: 0.72rem; color: #64748B;">{freq} incident(s) flagged by human reviewers</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="background: #FEE2E2; color: #DC2626; font-size: 0.78rem; font-weight: 800; padding: 0.2rem 0.5rem; border-radius: 4px;">
                                {pct}% of issues
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recurring issues detected.")

    with col_dist:
        st.markdown("#### Content Risk Level Distribution")
        risk_dist = get_risk_distribution()
        r_low = risk_dist.get("LOW", 0)
        r_med = risk_dist.get("MEDIUM", 0)
        r_high = risk_dist.get("HIGH", 0)

        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(
                f"""
                <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 0.85rem; text-align: center;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #16A34A;">LOW RISK</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #15803D;">{r_low}</div>
                    <div style="font-size: 0.68rem; color: #65A30D;">Clean clearance</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                f"""
                <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 0.85rem; text-align: center;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #D97706;">MEDIUM RISK</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #B45309;">{r_med}</div>
                    <div style="font-size: 0.68rem; color: #92400E;">Minor qualifier need</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                f"""
                <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; padding: 0.85rem; text-align: center;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #DC2626;">HIGH RISK</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #B91C1C;">{r_high}</div>
                    <div style="font-size: 0.68rem; color: #7F1D1D;">Strict block</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # PRODUCTION CHARTS
    # =========================================================================
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown("#### Production by Brand")
        b_counts = {}
        for item in all_content:
            b = item.get("brand", "Unknown")
            b_counts[b] = b_counts.get(b, 0) + 1
        if b_counts:
            df_b = pd.DataFrame(list(b_counts.items()), columns=["Brand", "Volume"]).set_index("Brand")
            st.bar_chart(df_b, color="#D4AF37", height=200)

    with c_chart2:
        st.markdown("#### Distribution by Platform")
        p_counts = {}
        for item in all_content:
            p = item.get("platform", "Unknown")
            p_counts[p] = p_counts.get(p, 0) + 1
        if p_counts:
            df_p = pd.DataFrame(list(p_counts.items()), columns=["Platform", "Volume"]).set_index("Platform")
            st.bar_chart(df_p, color="#0D9488", height=200)

