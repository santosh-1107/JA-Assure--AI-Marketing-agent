"""
Styling and CSS injections for the JA Assure Review Dashboard.
Implements luxury InsurTech branding:
- Jade: Gold accent (#D4AF37)
- DoctorShield: Teal accent (#0D9488)
- Dark obsidian background, crisp status badges, and responsive cards.
"""

CUSTOM_CSS = """
<style>
/* Main theme overrides */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Background gradient */
.stApp {
    background: radial-gradient(circle at 10% 20%, rgba(13, 148, 136, 0.04) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(212, 175, 55, 0.05) 0%, transparent 40%),
                #0b0f17;
    color: #e2e8f0;
}

/* Top Navigation & Header */
.header-container {
    padding: 1.5rem 0 1rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 1.5rem;
}

.header-title {
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
}

.brand-pill-jade {
    background: rgba(212, 175, 55, 0.15);
    color: #e5c07b;
    border: 1px solid rgba(212, 175, 55, 0.4);
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.brand-pill-ds {
    background: rgba(13, 148, 136, 0.15);
    color: #2dd4bf;
    border: 1px solid rgba(13, 148, 136, 0.4);
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* KPI metric cards */
.metric-card {
    background: #131b2a;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: transform 0.15s ease, border-color 0.15s ease;
}

.metric-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
    transform: translateY(-2px);
}

.metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #f8fafc;
    margin: 0.2rem 0;
}

.metric-caption {
    font-size: 0.75rem;
    color: #64748b;
}

/* Marketing Asset Review Cards */
.content-card-jade {
    background: #121824;
    border-left: 4px solid #d4af37;
    border-top: 1px solid rgba(212, 175, 55, 0.2);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.content-card-ds {
    background: #121824;
    border-left: 4px solid #0d9488;
    border-top: 1px solid rgba(13, 148, 136, 0.2);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.content-card-fail {
    background: #181418;
    border-left: 4px solid #ef4444;
    border-top: 1px solid rgba(239, 68, 68, 0.3);
    border-right: 1px solid rgba(239, 68, 68, 0.15);
    border-bottom: 1px solid rgba(239, 68, 68, 0.15);
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.1);
}

/* Compliance Badges */
.badge-pass {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 0.25rem 0.7rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

.badge-fail {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.5);
    padding: 0.25rem 0.7rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

.badge-platform {
    background: #1e293b;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
}

.badge-cycle {
    background: #27272a;
    color: #a1a1aa;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
}

/* Compliance Reason Box */
.compliance-box-fail {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
}

.compliance-rule-title {
    color: #fca5a5;
    font-weight: 700;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
}

.compliance-rule-desc {
    color: #fecaca;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}

/* Content block preview */
.content-text-box {
    background: #0d121c;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.88rem;
    line-height: 1.55;
    color: #f1f5f9;
    white-space: pre-wrap;
    margin: 0.75rem 0;
}

/* Before / After comparison layout */
.diff-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
    margin-top: 1rem;
}

.diff-before {
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 1rem;
}

.diff-after {
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 8px;
    padding: 1rem;
}

/* Buttons */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.15s ease;
}

/* Custom tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 0.25rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    padding: 0.5rem 1rem;
    font-weight: 600;
    color: #94a3b8;
}

.stTabs [aria-selected="true"] {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #f8fafc !important;
}
</style>
"""
