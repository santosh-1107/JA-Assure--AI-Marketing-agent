"""
Pydantic schemas for JA Assure AI Marketing Agent API requests and responses.
Enforces strict Literal validation for Brands, Platforms, Content Types, and Feedback Tags.
Enforces numeric validation bounds on Cycle and Fit Score.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

BrandLiteral = Literal["Jade", "DoctorShield"]
PlatformLiteral = Literal["LinkedIn", "Instagram", "X"]
ContentTypeLiteral = Literal["post", "carousel", "tweet", "video_script"]
StatusLiteral = Literal["pending", "approved", "rejected", "scheduled"]
FeedbackTagLiteral = Literal[
    "too_salesy",
    "inaccurate_claim",
    "off_brand_tone",
    "wrong_cta",
    "unsupported_claim",
    "unsupported_guarantee",
    "missing_qualifier",
    "aggressive_urgency",
    "human_edit",
    "other",
]
GenerationModeLiteral = Literal["groq", "gemini", "offline", "simulation", "test_mock"]


# =====================================================================
# Compliance Schemas
# =====================================================================

class ComplianceReason(BaseModel):
    rule: str = Field(..., description="Unique compliance rule identifier, e.g., NO_GUARANTEED_PAYOUT")
    severity: Optional[str] = Field("HIGH", description="CRITICAL, HIGH, MODERATE")
    category: Optional[str] = Field(None, description="Regulatory or brand category")
    message: str = Field(..., description="Specific explanation of why the rule was triggered")
    matched_phrase: Optional[str] = Field(None, description="The specific non-compliant phrase detected")
    reference: Optional[str] = Field(None, description="Regulatory standard or internal governance policy citation")


class ComplianceResult(BaseModel):
    status: str = Field(..., description="'PASS' / 'pass' or 'FAIL' / 'fail'")
    risk_level: Optional[str] = Field("LOW", description="LOW | MEDIUM | HIGH")
    risk_score: Optional[float] = Field(0.0, description="0.0 to 100.0 risk score calculated from detected issues")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Structured issues with rule_id, severity, evidence, explanation")
    reasons: List[ComplianceReason] = Field(default_factory=list, description="List of triggered compliance violations")


class ComplianceCheckRequest(BaseModel):
    brand: BrandLiteral = Field(..., description="Jade or DoctorShield")
    content: str = Field(..., min_length=5, description="Marketing content text to evaluate")


# =====================================================================
# Content Generation Schemas
# =====================================================================

class ContentGenerateRequest(BaseModel):
    brand: BrandLiteral = Field("Jade", description="Brand: Jade or DoctorShield")
    platform: PlatformLiteral = Field("LinkedIn", description="Platform: LinkedIn, Instagram, X")
    content_type: ContentTypeLiteral = Field("post", description="Type: post, carousel, tweet, video_script")
    topic: str = Field(..., min_length=3, description="Topic or marketing idea")
    product: Optional[str] = Field(None, description="Specific product, e.g. Jewellers Block & Specie")
    cycle: int = Field(1, ge=1, description="Generation cycle for tracking rejection rate trend (>= 1)")
    force_trigger_flaw: Optional[bool] = Field(
        False, 
        description="Demo helper: If True, forces generation of a known compliance flaw for rejection demo"
    )
    allow_offline_fallback: Optional[bool] = Field(
        True,
        description="If True, falls back to offline engine when API keys are not configured"
    )
    research_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional pre-fetched official JA Assure research context"
    )
    additional_instruction: Optional[str] = Field(
        None,
        description="Optional custom instruction to append to the generation prompt"
    )


class ResearchRequest(BaseModel):
    brand: BrandLiteral = Field("Jade", description="Jade or DoctorShield")
    topic: str = Field(..., min_length=3, description="Topic or marketing idea")
    product: Optional[str] = Field(None, description="Optional product category")
    competitor_list: Optional[List[str]] = Field(None, description="Optional competitor list for contrast analysis")


class SourceItem(BaseModel):
    title: str
    url: str
    source_type: str = Field("official_ja_assure", description="official_pdf or official_ja_assure or web_research")
    filename: Optional[str] = None
    page_number: Optional[int] = 1
    section: Optional[str] = "General"
    vertical: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = Field(1.0, ge=0.0)
    key_facts: List[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    summary: str
    changes: List[str] = Field(default_factory=list)
    recommendation: str
    sources: List[SourceItem] = Field(default_factory=list)
    competitor_analysis: Optional[Dict[str, Any]] = None
    web_research_status: Optional[str] = "EXTERNAL RESEARCH UNAVAILABLE (OFFLINE MODE)"
    is_live_search: Optional[bool] = False


class ContentItemResponse(BaseModel):
    id: int
    brand: str
    platform: str
    content_type: str
    topic: Optional[str] = None
    product: Optional[str] = None
    content: str
    status: str
    compliance_result: Optional[ComplianceResult] = None
    cycle: int
    parent_id: Optional[int] = None
    fixed_issue: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    retrieved_sources: Optional[List[Dict[str, Any]]] = None
    generation_mode: Optional[str] = "offline"
    provider: Optional[str] = "offline"
    model: Optional[str] = "offline-engine"
    prompt_version: Optional[str] = "1.0"
    knowledge_source_ids: Optional[List[str]] = None
    feedback_ids: Optional[List[int]] = None
    feedback_context_ids: Optional[List[int]] = None
    generation_metadata: Optional[Dict[str, Any]] = None
    claim_grounding: Optional[List[Dict[str, Any]]] = None
    claims_used: Optional[List[Dict[str, Any]]] = None
    uncertain_claims: Optional[List[str]] = None
    feedback_applied: Optional[List[str]] = None
    risk_level: Optional[str] = "LOW"
    risk_score: Optional[float] = 0.0
    variant_id: Optional[str] = None
    variants: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# =====================================================================
# Review Action Schemas
# =====================================================================

class RejectRequest(BaseModel):
    tag: FeedbackTagLiteral = Field(..., description="Rejection reason tag")
    note: str = Field(..., min_length=3, description="Required free-text explanation of rejection reason")
    issue_type: Optional[str] = Field(None, description="Standardized issue type for risk heatmap")
    corrected_content: Optional[str] = Field(None, description="Optional reviewer corrected version")
    risk_score: Optional[float] = Field(None, description="Assigned risk score")
    compliance_rule: Optional[str] = Field(None, description="Violated rule ID citation")


class EditRequest(BaseModel):
    edited_content: str = Field(..., min_length=5, description="New modified content text")
    tag: Optional[FeedbackTagLiteral] = Field("human_edit", description="Optional categorization of the edit")
    note: Optional[str] = Field(None, description="Optional note describing why the edit was made")
    issue_type: Optional[str] = Field(None, description="Standardized issue type")
    compliance_rule: Optional[str] = Field(None, description="Compliance rule ID")


class RegenerateRequest(BaseModel):
    additional_instruction: Optional[str] = Field(
        None, 
        description="Optional supplementary instruction for regeneration"
    )


# =====================================================================
# Feedback & Learning Schemas
# =====================================================================

class FeedbackItemResponse(BaseModel):
    id: int
    content_id: int
    brand: str
    tag: str
    note: str
    created_at: str
    original_content: Optional[str] = None
    corrected_content: Optional[str] = None
    issue_type: Optional[str] = None
    product: Optional[str] = None
    platform: Optional[str] = None
    risk_score: Optional[float] = 0.0
    compliance_rule: Optional[str] = None


class RejectionRateCycleItem(BaseModel):
    cycle: int
    total: int
    rejected: int
    approved: int
    rejection_rate: float


class RejectionRateResponse(BaseModel):
    cycles: List[RejectionRateCycleItem]
    total_reviewed: int
    overall_rejection_rate: float


class BeforeAfterComparison(BaseModel):
    child_id: int
    brand: str
    platform: str
    content_type: str
    topic: Optional[str] = None
    regenerated_content: str
    child_status: str
    child_compliance: Optional[ComplianceResult] = None
    fixed_issue: Optional[str] = None
    child_sources: Optional[List[Dict[str, Any]]] = None
    child_generation_mode: Optional[str] = "offline"
    child_created_at: Optional[str] = None
    parent_id: int
    parent_topic: Optional[str] = None
    original_content: str
    parent_compliance: Optional[ComplianceResult] = None
    parent_sources: Optional[List[Dict[str, Any]]] = None
    feedback_tag: Optional[str] = None
    feedback_note: Optional[str] = None


# =====================================================================
# Leads Schemas
# =====================================================================

class LeadCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    contact: Optional[str] = None
    vertical: str = Field(..., min_length=2)
    region: str = Field("Singapore", min_length=2)
    fit_score: int = Field(50, ge=0, le=100, description="Criteria-driven fit score (0-100)")
    outreach_draft: Optional[str] = None
    source: Optional[str] = "manual_entry"
    source_url: Optional[str] = None
    scoring_breakdown: Optional[Dict[str, Any]] = None


class LeadDiscoveryRequest(BaseModel):
    vertical: str = Field(..., min_length=2)
    region: str = Field("Singapore", min_length=2)
    search_terms: Optional[str] = None


class LeadItemResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    vertical: str
    region: Optional[str] = "Singapore"
    fit_score: int
    outreach_draft: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    scoring_breakdown: Optional[Dict[str, Any]] = None
    status: str
    created_at: Optional[str] = None


# Aliases for convenience
GenerateRequest = ContentGenerateRequest
LeadCreate = LeadCreateRequest
