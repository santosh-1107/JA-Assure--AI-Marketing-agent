"""
Analytics Component for JA Assure.
Visualizes marketing production volume, compliance pass rates, and platform distributions.
"""

import pandas as pd
import streamlit as st
from backend import models


def render_analytics_page():
    """
    Renders enterprise analytics workspace with real database queries.
    """
    st.markdown("### Operational Analytics")
    st.caption("Content volume, compliance pass rates, platform distribution, and reviewer decision velocity.")

    all_content = models.list_all_content()
    approved = models.list_approved_content()
    pending = models.list_pending_content()
    
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

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown("#### Production by Brand")
        b_counts = {}
        for item in all_content:
            b = item.get("brand", "Unknown")
            b_counts[b] = b_counts.get(b, 0) + 1
        if b_counts:
            df_b = pd.DataFrame(list(b_counts.items()), columns=["Brand", "Volume"]).set_index("Brand")
            st.bar_chart(df_b, color="#D4AF37", height=220)

    with c_chart2:
        st.markdown("#### Distribution by Platform")
        p_counts = {}
        for item in all_content:
            p = item.get("platform", "Unknown")
            p_counts[p] = p_counts.get(p, 0) + 1
        if p_counts:
            df_p = pd.DataFrame(list(p_counts.items()), columns=["Platform", "Volume"]).set_index("Platform")
            st.bar_chart(df_p, color="#0D9488", height=220)
