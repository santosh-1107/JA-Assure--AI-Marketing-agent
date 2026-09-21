"""
Pydantic schemas for JA Assure AI Marketing Agent API requests and responses.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =====================================================================
# Compliance Schemas
# =====================================================================

class ComplianceReason(BaseModel):
    rule: str = Field(..., description="Unique compliance rule identifier, e.g., NO_GUARANTEED_PAYOUT")
    category: Optional[str] = Field(None, description="Regulatory category (e.g. MAS Insurance Ad Guidelines)")
    message: str = Field(..., description="Specific explanation of why the rule was triggered")
    matched_phrase: Optional[str] = Field(None, description="The specific non-compliant phrase detected")


class ComplianceResult(BaseModel):
    status: str = Field(..., description="'pass' or 'fail'")
    reasons: List[ComplianceReason] = Field(default_factory=list, description="List of triggered compliance violations")


class ComplianceCheckRequest(BaseModel):
    brand: str = Field(..., description="Jade or DoctorShield")
    content: str = Field(..., description="Marketing content text to evaluate")


# =====================================================================
# Content Generation Schemas
# =====================================================================

class ContentGenerateRequest(BaseModel):
    brand: str = Field("Jade", description="Brand name: Jade or DoctorShield")
    platform: str = Field("LinkedIn", description="Platform: LinkedIn, Instagram, X")
    content_type: str = Field("post", description="Type: post, carousel, tweet, video_script")
    topic: str = Field(..., description="Topic or marketing idea")
    cycle: int = Field(1, description="Generation cycle for tracking rejection rate trend")
    force_trigger_flaw: Optional[bool] = Field(
        False, 
        description="Demo helper: If True, forces generation of a known compliance flaw for rejection demo"
    )
    research_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional pre-fetched official JA Assure research context"
    )


class ResearchRequest(BaseModel):
    brand: str = Field("Jade", description="Jade or DoctorShield")
    topic: str = Field(..., description="Topic or marketing idea")
    competitor_list: Optional[List[str]] = Field(None, description="Optional competitor list")


class SourceItem(BaseModel):
    title: str
    url: str
    vertical: Optional[str] = None
    snippet: Optional[str] = None
    key_facts: List[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    summary: str
    changes: List[str] = Field(default_factory=list)
    recommendation: str
    sources: List[SourceItem] = Field(default_factory=list)


class ContentItemResponse(BaseModel):
    id: int
    brand: str
    platform: str
    content_type: str
    content: str
    status: str
    compliance_result: Optional[ComplianceResult] = None
    cycle: int
    parent_id: Optional[int] = None
    fixed_issue: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None


# =====================================================================
# Review Action Schemas
# =====================================================================

class RejectRequest(BaseModel):
    tag: str = Field(..., description="Feedback tag: too_salesy, inaccurate_claim, off_brand_tone, wrong_cta, other")
    note: str = Field(..., min_length=3, description="Required free-text explanation of rejection reason")


class EditRequest(BaseModel):
    edited_content: str = Field(..., min_length=5, description="New modified content text")
    tag: Optional[str] = Field(None, description="Optional categorization of the edit")
    note: Optional[str] = Field(None, description="Optional note describing why the edit was made")


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
    platform: Optional[str] = None


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
    regenerated_content: str
    child_status: str
    child_compliance: Optional[ComplianceResult] = None
    fixed_issue: Optional[str] = None
    child_sources: Optional[List[Dict[str, Any]]] = None
    child_created_at: Optional[str] = None
    parent_id: int
    original_content: str
    parent_compliance: Optional[ComplianceResult] = None
    parent_sources: Optional[List[Dict[str, Any]]] = None
    feedback_tag: Optional[str] = None
    feedback_note: Optional[str] = None


# =====================================================================
# Leads Schemas (P1)
# =====================================================================

class LeadCreateRequest(BaseModel):
    name: str
    contact: str
    vertical: str
    fit_score: int = 50
    outreach_draft: Optional[str] = None


class LeadItemResponse(BaseModel):
    id: int
    name: str
    contact: str
    vertical: str
    fit_score: int
    outreach_draft: Optional[str] = None
    status: str
    created_at: Optional[str] = None
