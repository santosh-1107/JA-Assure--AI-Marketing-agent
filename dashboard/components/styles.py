"""
Enterprise InsurTech Stylesheet for JA Assure AI Marketing & Compliance Platform.
Faithfully reproduces the reference design:
- Deep navy sidebar (#0B1220 / #0F172A)
- Crisp white/light-gray workspace (#F8FAFC / #F1F5F9)
- White elevated cards with subtle borders (#E2E8F0)
- JADE Gold (#D4AF37) and DOCTORSHIELD Teal (#0D9488) accents
- PASS (#059669) and FAIL (#DC2626) governance tokens
- Precise typography, 6-8px border radius, clean enterprise spacing
"""

ENTERPRISE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-workspace: #F8FAFC;
    --bg-card: #FFFFFF;
    --border-card: #E2E8F0;
    --border-card-hover: #CBD5E1;
    --text-main: #0F172A;
    --text-muted: #64748B;
    --text-light: #94A3B8;
    
    --sidebar-bg: #0B1220;
    --sidebar-active: #151F32;
    --sidebar-border: #1E293B;
    
    --jade-gold: #D4AF37;
    --jade-btn: #E5C07B;
    --ds-teal: #0D9488;
    
    --pass-green: #059669;
    --pass-bg: #F0FDF4;
    --pass-border: #BBF7D0;
    
    --fail-red: #DC2626;
    --fail-bg: #FEF2F2;
    --fail-border: #FECACA;
}

/* Global Reset */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-main);
}

.stApp {
    background-color: var(--bg-workspace) !important;
}

/* Hide default streamlit decoration */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 1560px !important;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-right: 1px solid var(--sidebar-border) !important;
    min-width: 240px !important;
    max-width: 250px !important;
}
section[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 0.75rem !important;
}

/* Sidebar Logo & Wordmark */
.sidebar-brand-wrapper {
    padding: 0.5rem 0.25rem 1.25rem 0.25rem;
    border-bottom: 1px solid var(--sidebar-border);
    margin-bottom: 1rem;
}
.sidebar-brand-row {
    display: flex;
    align-items: center;
    gap: 0.65rem;
}
.brand-logo-petals {
    width: 32px;
    height: 32px;
}
.brand-logo-text {
    font-size: 1.25rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.02em;
    line-height: 1.1;
}
.brand-logo-tagline {
    font-size: 0.55rem;
    color: #D4AF37;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.25rem;
}

/* Sidebar Buttons */
section[data-testid="stSidebar"] div.stButton > button {
    background: transparent !important;
    color: #CBD5E1 !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 0.5rem 0.75rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    margin-bottom: 0.15rem !important;
}
section[data-testid="stSidebar"] div.stButton > button:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: #151F32 !important;
    color: #FFFFFF !important;
    border-left: 3px solid #D4AF37 !important;
    border-radius: 0 6px 6px 0 !important;
    font-weight: 700 !important;
}

/* Sidebar Region Footer */
.sidebar-region-footer {
    margin-top: 1.75rem;
    padding-top: 1rem;
    border-top: 1px solid var(--sidebar-border);
}
.region-label {
    font-size: 0.68rem;
    color: var(--text-light);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.region-pill {
    background: #151F32;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 0.35rem 0.65rem;
    font-size: 0.76rem;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.flags-row {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.65rem;
    font-size: 1.05rem;
}
.region-tagline {
    font-size: 0.68rem;
    color: #94A3B8;
    margin-top: 0.35rem;
    line-height: 1.35;
}

/* Top Application Header */
.app-header-container {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 0.85rem 1.25rem;
    margin-bottom: 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}
.header-title-box {
    display: flex;
    flex-direction: column;
}
.header-main-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.01em;
}
.header-main-sub {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}
.header-right-group {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.user-avatar-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #F59E0B;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 0.78rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Product Hero Panels (JADE & DOCTORSHIELD) */
.product-panel {
    border-radius: 10px;
    padding: 1.4rem;
    min-height: 240px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}
.panel-jade {
    background-color: #0B111E;
    border: 1px solid rgba(212, 175, 55, 0.4);
}
.panel-ds {
    background-color: #061923;
    border: 1px solid rgba(13, 148, 136, 0.4);
}
.panel-content-layer {
    position: relative;
    z-index: 2;
    max-width: 68%;
}
.panel-brand-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.65rem;
}
.panel-brand-title {
    font-size: 1.10rem;
    font-weight: 800;
    letter-spacing: 0.06em;
}
.title-jade { color: #D4AF37; }
.title-ds { color: #2DD4BF; }
.panel-brand-sub {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.panel-headline {
    font-size: 1.30rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.25;
    margin-bottom: 0.45rem;
    letter-spacing: -0.01em;
}
.panel-body-desc {
    font-size: 0.78rem;
    color: rgba(255, 255, 255, 0.85);
    line-height: 1.45;
    margin-bottom: 0.85rem;
}
.panel-footer-note {
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.5);
    margin-top: 0.5rem;
}

/* Metric Strip (5 Horizontal Cards) */
.metric-card-box {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 0.75rem 0.95rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}
.metric-card-top {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.25rem;
}
.metric-icon-circle {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.70rem;
}
.metric-card-label {
    font-size: 0.70rem;
    font-weight: 700;
    color: var(--text-muted);
}
.metric-value-row {
    display: flex;
    align-items: baseline;
    gap: 0.40rem;
}
.metric-card-number {
    font-size: 1.45rem;
    font-weight: 800;
    color: var(--text-main);
    letter-spacing: -0.02em;
}
.metric-card-trend {
    font-size: 0.70rem;
    font-weight: 700;
}
.metric-card-sub {
    font-size: 0.68rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}

/* Main Review Workspace Layout */
.workspace-section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.85rem;
}
.section-title-with-bar {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
}
.section-bar {
    width: 3px;
    height: 18px;
    background: #D4AF37;
    border-radius: 2px;
}
.section-title-text {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--text-main);
}
.section-sub-text {
    font-size: 0.76rem;
    color: var(--text-muted);
    margin-left: 0.75rem;
}

/* Horizontal Review Cards */
.review-row-card {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    margin-bottom: 0.85rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    overflow: hidden;
}
.card-border-fail {
    border-left: 4px solid var(--fail-red) !important;
}
.card-border-pass {
    border-left: 4px solid var(--pass-green) !important;
}
.review-card-topbar {
    padding: 0.60rem 0.95rem;
    background: #F8FAFC;
    border-bottom: 1px solid #F1F5F9;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.topbar-meta-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.pill-badge {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
.pill-jade { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.pill-ds { background: #CCFBF1; color: #115E59; border: 1px solid #99F6E4; }
.pill-neutral { background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }

.review-content-title {
    font-size: 0.92rem;
    font-weight: 800;
    color: var(--text-main);
    margin-bottom: 0.30rem;
}
.review-content-body {
    font-size: 0.80rem;
    color: #334155;
    line-height: 1.5;
    margin-bottom: 0.60rem;
}
.review-tags-row {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.50rem;
    flex-wrap: wrap;
}
.content-tag {
    background: #F1F5F9;
    color: #475569;
    border-radius: 4px;
    padding: 0.12rem 0.40rem;
    font-size: 0.68rem;
    font-weight: 600;
}
.grounding-indicator {
    font-size: 0.72rem;
    color: #2563EB;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.30rem;
}

/* Compliance Gate Box */
.compliance-gate-box {
    border-radius: 6px;
    padding: 0.70rem 0.80rem;
}
.box-fail {
    background: var(--fail-bg);
    border: 1px solid var(--fail-border);
}
.box-pass {
    background: var(--pass-bg);
    border: 1px solid var(--pass-border);
}
.gate-status-text-fail {
    font-size: 0.74rem;
    font-weight: 800;
    color: var(--fail-red);
    margin-bottom: 0.30rem;
}
.gate-status-text-pass {
    font-size: 0.74rem;
    font-weight: 800;
    color: var(--pass-green);
    margin-bottom: 0.30rem;
}
.violation-pill {
    background: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FCA5A5;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.12rem 0.40rem;
    border-radius: 4px;
    display: inline-block;
    margin: 0.2rem 0;
}
.violation-reason {
    font-size: 0.72rem;
    color: #7F1D1D;
    line-height: 1.35;
    margin-top: 0.20rem;
}

/* Right Rail Widgets */
.right-widget-card {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}
.quote-box {
    font-style: italic;
    font-size: 0.82rem;
    color: #1E293B;
    line-height: 1.5;
    margin-bottom: 0.4rem;
}
.widget-header {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.65rem;
}
.widget-title {
    font-size: 0.88rem;
    font-weight: 800;
    color: var(--text-main);
}
.widget-sub {
    font-size: 0.70rem;
    color: var(--text-muted);
}
.resource-list-item {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid #F1F5F9;
}
.resource-thumb {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    background: #E2E8F0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
}
.resource-item-title {
    font-size: 0.76rem;
    font-weight: 700;
    color: var(--text-main);
    line-height: 1.25;
}
.resource-item-sub {
    font-size: 0.68rem;
    color: var(--text-muted);
}

/* Feedback stream item */
.feedback-stream-item {
    padding: 0.50rem 0;
    border-bottom: 1px solid #F1F5F9;
}
.fb-tag-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.20rem;
}
.fb-text {
    font-size: 0.76rem;
    color: #334155;
    line-height: 1.35;
}

/* Action Buttons inside workspace */
div.stButton > button {
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    padding: 0.35rem 0.75rem !important;
    transition: all 0.15s ease !important;
}
/* Selectbox & Inputs inside light workspace */
div[data-baseweb="select"] {
    background-color: #FFFFFF !important;
    border-radius: 6px !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-card) !important;
    color: var(--text-main) !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0D9488 !important;
    box-shadow: 0 0 0 1px #0D9488 !important;
}
</style>
"""
