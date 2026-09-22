"""
Dual Product Workspace Component (JADE & DOCTORSHIELD) for JA Assure.
Faithfully renders the high-end product campaign modules with background photography.
"""

import base64
import streamlit as st
from pathlib import Path

# Load local assets as base64 data URIs
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
JADE_IMG_PATH = ASSETS_DIR / "jade_hero.jpg"
DS_IMG_PATH = ASSETS_DIR / "doctorshield_hero.jpg"

_jade_b64 = ""
_ds_b64 = ""

if JADE_IMG_PATH.exists():
    with open(JADE_IMG_PATH, "rb") as f:
        _jade_b64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

if DS_IMG_PATH.exists():
    with open(DS_IMG_PATH, "rb") as f:
        _ds_b64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"


def render_product_panels():
    """
    Renders two large horizontal product campaign panels side-by-side:
    - JADE (Jewellers Block & Specie Insurance)
    - DOCTORSHIELD (Medical Indemnity Insurance)
    """
    col_jade, col_ds = st.columns(2)

    with col_jade:
        bg_style = f"background: linear-gradient(to right, rgba(11, 17, 30, 0.98) 0%, rgba(11, 17, 30, 0.88) 55%, rgba(11, 17, 30, 0.4) 100%), url('{_jade_b64}') right center / cover no-repeat;" if _jade_b64 else "background: #0B111E;"
        st.markdown(
            f"""
            <div class="product-panel panel-jade" style="{bg_style}">
                <div class="panel-content-layer">
                    <div class="panel-brand-header">
                        <span style="font-size: 1.1rem; color: #D4AF37;">◆</span>
                        <div>
                            <span class="panel-brand-title title-jade">JADE</span>
                            <div class="panel-brand-sub" style="color: #E5C07B;">JEWELLERS BLOCK & SPECIE INSURANCE</div>
                        </div>
                    </div>
                    <div class="panel-headline">Specialist protection for jewellery businesses</div>
                    <div class="panel-body-desc">
                        Comprehensive coverage for jewellers, gold bullion distributors, luxury watch dealers and high-value assets. Built on deep industry expertise.
                    </div>
                </div>
                <div style="position: relative; z-index: 2;">
                    <div class="panel-footer-note">Protecting what matters most. Today and tomorrow.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate Jade Content →", key="btn_hero_jade", type="primary", use_container_width=True):
            st.session_state["active_page"] = "Generate Content"
            st.session_state["gen_brand"] = "Jade"
            st.rerun()

    with col_ds:
        bg_style_ds = f"background: linear-gradient(to right, rgba(6, 25, 35, 0.98) 0%, rgba(6, 25, 35, 0.88) 55%, rgba(6, 25, 35, 0.4) 100%), url('{_ds_b64}') right center / cover no-repeat;" if _ds_b64 else "background: #061923;"
        st.markdown(
            f"""
            <div class="product-panel panel-ds" style="{bg_style_ds}">
                <div class="panel-content-layer">
                    <div class="panel-brand-header">
                        <span style="font-size: 1.1rem; color: #2DD4BF;">🛡</span>
                        <div>
                            <span class="panel-brand-title title-ds">DOCTORSHIELD</span>
                            <div class="panel-brand-sub" style="color: #5EEAD4;">MEDICAL INDEMNITY INSURANCE</div>
                        </div>
                    </div>
                    <div class="panel-headline">Professional protection for healthcare professionals</div>
                    <div class="panel-body-desc">
                        Medico-legal defence, professional indemnity and patient safety solutions for doctors, specialists and healthcare institutions across Asia.
                    </div>
                </div>
                <div style="position: relative; z-index: 2;">
                    <div class="panel-footer-note">Supporting those who care for others.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate DoctorShield Content →", key="btn_hero_ds", type="secondary", use_container_width=True):
            st.session_state["active_page"] = "Generate Content"
            st.session_state["gen_brand"] = "DoctorShield"
            st.rerun()

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
