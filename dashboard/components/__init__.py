"""
Enterprise UI Components Package for JA Assure.
"""

from dashboard.components.styles import ENTERPRISE_CSS
from dashboard.components.sidebar import render_sidebar
from dashboard.components.header import render_header
from dashboard.components.product_panels import render_product_panels
from dashboard.components.metrics import render_metric_strip
from dashboard.components.review import render_review_card, render_review_detail_workspace
from dashboard.components.compliance import format_compliance_box
from dashboard.components.knowledge import render_knowledge_right_widget, render_knowledge_library_page
from dashboard.components.feedback import render_feedback_right_widget, render_feedback_learning_page
from dashboard.components.analytics import render_analytics_page

__all__ = [
    "ENTERPRISE_CSS",
    "render_sidebar",
    "render_header",
    "render_product_panels",
    "render_metric_strip",
    "render_review_card",
    "render_review_detail_workspace",
    "format_compliance_box",
    "render_knowledge_right_widget",
    "render_knowledge_library_page",
    "render_feedback_right_widget",
    "render_feedback_learning_page",
    "render_analytics_page",
]
