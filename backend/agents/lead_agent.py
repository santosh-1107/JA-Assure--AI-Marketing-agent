"""
Lead Agent for JA Assure AI Marketing Agent.
Discovers and scores prospective B2B InsurTech leads across target verticals and regions.
Calculates fit score from explicit criteria (0-100) and crafts tailored compliant outreach drafts.
Strictly prohibits fabricating personal contact details or fake email addresses.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from backend.agents.research_agent import research_agent

logger = logging.getLogger(__name__)

SUPPORTED_VERTICALS = {"Jewellers", "Clinics", "SMEs", "Couriers"}
SUPPORTED_REGIONS = {"Singapore", "Malaysia", "Indonesia", "Thailand", "Vietnam"}


def calculate_fit_score(
    vertical: str,
    region: str,
    has_high_value_exposure: bool = True,
    has_statutory_license_requirement: bool = True,
    has_verifiable_entity: bool = True,
) -> Dict[str, Any]:
    """
    Explicit multi-criteria scoring algorithm for InsurTech prospects:
    1. vertical_match: 0 - 25 points
    2. region_match: 0 - 20 points
    3. business_profile: 0 - 20 points
    4. insurance_relevance: 0 - 20 points
    5. public_information_quality: 0 - 15 points
    Total: 0 - 100 points
    """
    # 1. Vertical Match (max 25)
    v_clean = vertical.strip().capitalize()
    if v_clean in ("Jewellers", "Jewelry", "Clinics", "Medical"):
        v_score = 25
    elif v_clean in ("Smes", "Specie", "Healthcare"):
        v_score = 20
    elif v_clean in ("Couriers", "Logistics"):
        v_score = 15
    else:
        v_score = 10

    # 2. Region Match (max 20)
    r_clean = region.strip().capitalize()
    if r_clean == "Singapore":
        r_score = 20
    elif r_clean == "Malaysia":
        r_score = 18
    elif r_clean in ("Indonesia", "Thailand", "Vietnam"):
        r_score = 15
    else:
        r_score = 8

    # 3. Business Profile Risk Exposure (max 20)
    b_score = 18 if has_high_value_exposure else 10

    # 4. Insurance / Underwriting Relevance (max 20)
    i_score = 19 if has_statutory_license_requirement else 12

    # 5. Public Information Verifiability (max 15)
    p_score = 14 if has_verifiable_entity else 5

    total = v_score + r_score + b_score + i_score + p_score
    total_clamped = max(0, min(100, total))

    return {
        "fit_score": total_clamped,
        "breakdown": {
            "vertical_match": v_score,
            "region_match": r_score,
            "business_profile": b_score,
            "insurance_relevance": i_score,
            "public_information_quality": p_score,
        },
    }


def generate_outreach_draft(name: str, vertical: str, region: str) -> str:
    """Generate professional, compliant B2B introductory copy."""
    v_clean = vertical.strip().capitalize()
    if v_clean in ("Jewellers", "Jewelry", "Specie"):
        return (
            f"Dear {name}, fine jewellery trade operations in {region} manage significant vault and transit risk. "
            "JA Assure's Jade Jewellers Block provides commercial trade underwriting under Lloyd's syndicate coverholder authority. "
            "We would welcome an opportunity to review your vault specifications and stock movement schedules: jadeassure.com/bespoke"
        )
    elif v_clean in ("Clinics", "Medical"):
        return (
            f"Dear {name}, clinical practice in {region} involves evolving disciplinary and litigation considerations. "
            "DoctorShield provides retroactive professional indemnity and specialized medico-legal defense counsel. "
            "We would welcome a confidential consultation regarding your practice's retroactive coverage date: doctorshield.com/advisory"
        )
    else:
        return (
            f"Dear {name}, specialized commercial operations require disciplined underwriting. "
            f"JA Assure offers risk-engineered insurance solutions tailored for {region} commercial entities. "
            "Explore our underwriting capabilities: ja-assure.com"
        )


class LeadAgent:
    """
    Lead discovery and scoring agent.
    Evaluates verified entities against insurance underwriting criteria.
    Never fabricates personal contacts or emails.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def score_lead(
        self,
        name: str,
        vertical: str,
        region: str = "Singapore",
        contact: Optional[str] = None,
        source: str = "manual_entry",
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Score an identified prospect entity using explicit InsurTech criteria."""
        scoring = calculate_fit_score(
            vertical=vertical,
            region=region,
            has_high_value_exposure=True,
            has_statutory_license_requirement=True,
            has_verifiable_entity=bool(source_url or contact),
        )

        outreach = generate_outreach_draft(name=name, vertical=vertical, region=region)

        return {
            "name": name,
            "contact": contact if (contact and "@" in contact) else None,
            "vertical": vertical,
            "region": region,
            "fit_score": scoring["fit_score"],
            "scoring_breakdown": scoring["breakdown"],
            "outreach_draft": outreach,
            "source": source,
            "source_url": source_url or "https://www.ja-assure.com/resources.html",
        }

    def discover_leads(
        self,
        vertical: str,
        region: str = "Singapore",
        search_terms: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover genuine prospect entities via research.
        If live web research is unavailable or yields no verified directories,
        returns no leads rather than inventing fake individuals.
        """
        tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
        discovered = []

        if tavily_key and len(tavily_key) > 5:
            try:
                query = f"{vertical} businesses clinics directories in {region} {search_terms or ''}".strip()
                res = research_agent._search_tavily(query=query, api_key=tavily_key)
                for item in res:
                    title = item.get("title", "")
                    # Extract clean organization name from title
                    clean_name = title.split("-")[0].split("|")[0].strip()
                    if len(clean_name) > 3:
                        lead = self.score_lead(
                            name=clean_name,
                            vertical=vertical,
                            region=region,
                            contact=None,  # NEVER fabricate email without verified directory confirmation
                            source="live_research",
                            source_url=item.get("url"),
                        )
                        discovered.append(lead)
            except Exception as e:
                logger.warning(f"Live lead discovery error: {e}")

        # If no verified live research exists, return empty list (NO FABRICATION)
        return discovered


# Global lead agent instance
lead_agent = LeadAgent()
