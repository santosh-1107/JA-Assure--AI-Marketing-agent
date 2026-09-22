"""
Demo Seeding Script for JA Assure AI Marketing Agent.
Populates an ISOLATED SQLite demo database (data/demo/ja_assure_demo.db) with multi-cycle records demonstrating:
1. Downward rejection rate trend (80% -> 60% -> 40% -> 20%) backed by real rows.
2. Distinct brand voices (Jade vs. DoctorShield).
3. Before / After regeneration evidence with linked parent_ids.
4. Pending items ready for the live hackathon demonstration.
5. High-scoring InsurTech leads (P1).

STRICT DEMO ISOLATION:
This script operates on data/demo/ja_assure_demo.db and CANNOT modify data/ja_assure.db unless DEMO_MODE=true.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    init_db,
    get_connection,
    get_db_path,
    is_demo_mode,
    DEFAULT_DB_PATH,
    DEMO_DB_PATH,
)
from backend import models
from backend.knowledge.ja_assure_sources import load_all_sources


def seed_data(db_path: Optional[str] = None):
    """
    Seed isolated demo dataset into SQLite.
    Refuses to execute against the production/local database unless DEMO_MODE=true.
    """
    target_path = Path(db_path) if db_path else DEMO_DB_PATH
    prod_path = DEFAULT_DB_PATH.resolve()

    if target_path.resolve() == prod_path and not is_demo_mode():
        raise PermissionError(
            "CRITICAL GOVERNANCE ERROR: scripts/seed_demo.py cannot modify the production database (data/ja_assure.db). "
            "Seeding is strictly confined to data/demo/ja_assure_demo.db unless DEMO_MODE=true is explicitly enabled."
        )

    # Force environment path for this process
    os.environ["JA_ASSURE_DB_PATH"] = str(target_path)

    print(f"[Seed] Initializing fresh demo SQLite database at: {target_path} ...")
    init_db(str(target_path))

    conn = get_connection(str(target_path))
    cursor = conn.cursor()

    # Clear existing demo records to ensure clean reproducible demo state
    cursor.execute("DELETE FROM feedback;")
    cursor.execute("DELETE FROM content_queue;")
    cursor.execute("DELETE FROM leads;")
    conn.commit()
    conn.close()

    print("[Seed] Seeding multi-cycle marketing review data...")

    all_sources = load_all_sources()
    jade_source = [s for s in all_sources if s.get("id") == "jewellers_block"]
    ds_source = [s for s in all_sources if s.get("id") == "medical_indemnity"]

    # =========================================================================
    # CYCLE 1: Baseline (80% Rejection Rate — 4 Rejected, 1 Approved)
    # =========================================================================
    
    # C1 Item 1 (Jade - FAIL / REJECTED) -> Links to C2 regeneration!
    c1_fail_comp = {
        "status": "fail",
        "reasons": [
            {
                "rule": "NO_GUARANTEED_PAYOUT",
                "tier": "REGULATORY",
                "category": "Regulatory Prohibition on Guaranteed Outcomes",
                "severity": "CRITICAL",
                "message": "The content claims guaranteed claim payouts. Insurance regulations require clarifying settlements depend on underwriting review.",
                "matched_phrase": "guaranteed payouts",
                "reference": "General Insurance Advertising Standards — Prohibition on Guaranteed Payouts"
            },
            {
                "rule": "NO_GUARANTEED_PROTECTION",
                "tier": "REGULATORY",
                "category": "Regulatory Prohibition on Absolute Protection",
                "severity": "CRITICAL",
                "message": "The content uses absolute protection terminology ('100% protected').",
                "matched_phrase": "100% protected",
                "reference": "Fair Dealing Guidelines — Qualified Coverage Disclosures"
            }
        ]
    }
    c1_1 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic="Safeguarding multi-generational jewellery wealth and heirlooms",
        content=(
            "When safeguarding multi-generational wealth, standard insurance falls short.\n\n"
            "At Jade, we provide bespoke valuation and guaranteed payouts for high-value jewelry collections. "
            "Our private client solutions ensure your family's priceless heirlooms are 100% protected with instant payout guaranteed.\n\n"
            "Act now before your heritage is at risk. Connect with our private client team today."
        ),
        compliance_result=c1_fail_comp,
        cycle=1,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c1_1["id"],
        tag="inaccurate_claim",
        note="Insurance regulatory standards prohibit promising guaranteed claim payouts or claiming 100% protection without policy qualifiers.",
        db_path=str(target_path),
    )

    # C1 Item 2 (DoctorShield - FAIL / REJECTED)
    ds_c1_comp = {
        "status": "fail",
        "reasons": [
            {
                "rule": "NO_GUARANTEED_LEGAL_OUTCOME",
                "tier": "REGULATORY",
                "category": "Legal & Regulatory Prohibition",
                "severity": "CRITICAL",
                "message": "Prohibits guaranteeing court dismissal or zero malpractice liability.",
                "matched_phrase": "guaranteed dismissal",
                "reference": "Healthcare Professional Indemnity Ethics Code"
            },
            {
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "tier": "BRAND_POLICY",
                "category": "Professional Medical Dignity",
                "severity": "HIGH",
                "message": "Sensationalist scare tactics targeting physicians.",
                "matched_phrase": "patients will sue you tomorrow",
                "reference": "JA Assure Medical Dignity Policy"
            }
        ]
    }
    c1_2 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        topic="Clinical malpractice litigation risk and disciplinary defense",
        content=(
            "Clinical practice faces unprecedented legal scrutiny across Southeast Asia.\n\n"
            "DoctorShield provides medical practitioners with guaranteed dismissal of patient malpractice claims and zero risk of disciplinary action.\n\n"
            "Patients will sue you tomorrow if you don't act fast. Protect your license immediately."
        ),
        compliance_result=ds_c1_comp,
        cycle=1,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c1_2["id"],
        tag="inaccurate_claim",
        note="Never guarantee legal case dismissals and eliminate fearmongering phrases like 'patients will sue you tomorrow'.",
        db_path=str(target_path),
    )

    # C1 Item 3 (Jade - FAIL / REJECTED)
    c1_3 = models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        topic="Fine art and jewellery lifestyle safeguarding",
        content=(
            "Priceless jewelry deserves more than ordinary insurance! ✨💎\n\n"
            "Jade delivers bespoke protection with guaranteed payouts on every fine art and jewelry collection. "
            "100% protected, zero risk. Never worry about claim disputes again!\n\n"
            "👉 Tap link in bio now!"
        ),
        compliance_result=c1_fail_comp,
        cycle=1,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c1_3["id"],
        tag="inaccurate_claim",
        note="Avoid 'zero risk' and 'guaranteed payouts' on Instagram lifestyle posts.",
        db_path=str(target_path),
    )

    # C1 Item 4 (DoctorShield - FAIL / REJECTED)
    c1_4 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        topic="Physician indemnity awareness",
        content=(
            "Doctors: Patients will sue you tomorrow without indemnity. DoctorShield offers guaranteed dismissal and 100% protection. #MedTwitter"
        ),
        compliance_result=ds_c1_comp,
        cycle=1,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c1_4["id"],
        tag="too_salesy",
        note="Tone down aggressive threat headlines on X. Emphasize calm medico-legal advisory.",
        db_path=str(target_path),
    )

    # C1 Item 5 (Jade - PASS / APPROVED)
    c1_pass_comp = {"status": "pass", "reasons": []}
    c1_5 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic="Multi-generational heirloom safeguarding",
        content=(
            "Safeguarding multi-generational heirlooms requires more than standard coverage.\n\n"
            "At Jade, our bespoke policies offer private client valuation and structured claims assessment — subject to policy terms and underwriter schedule.\n\n"
            "Connect with our advisory desk: jadeassure.com/bespoke"
        ),
        compliance_result=c1_pass_comp,
        cycle=1,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c1_5["id"], db_path=str(target_path))

    # =========================================================================
    # CYCLE 2: Learning Applied (60% Rejection Rate — 3 Rejected, 2 Approved)
    # =========================================================================

    # C2 Item 1 (Jade - Regenerated from C1 Item 1! BEFORE/AFTER SHOWCASE)
    c2_1 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic="Safeguarding multi-generational jewellery wealth and heirlooms",
        content=(
            "Preserving multi-generational wealth and fine collections requires thoughtful advisory, not hasty assumptions.\n\n"
            "At Jade, our private client specialists work alongside collectors to provide bespoke asset valuation and comprehensive coverage for fine jewelry and heirloom portfolios.\n\n"
            "Key Advisory Principles:\n"
            "• Independent certified appraisal for rare heirlooms\n"
            "• Discretionary underwriting tailored to private client vaults\n"
            "• Structured claims assessment supported by dedicated specialist handlers\n\n"
            "All coverage terms, limits, and claims are subject to policy terms and conditions and underwriter schedule.\n\n"
            "Learn more about structured legacy safeguarding: jadeassure.com/private-client"
        ),
        compliance_result=c1_pass_comp,
        cycle=2,
        parent_id=c1_1["id"],
        fixed_issue="Removed guaranteed payout claims; added mandatory regulatory disclosure 'subject to policy terms and conditions'.",
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c2_1["id"], db_path=str(target_path))

    # C2 Item 2 (Jade - FAIL / REJECTED)
    c2_2 = models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        topic="Jewelry insurance pricing promotion",
        content="Looking for the cheapest luxury jewelry insurance in Singapore? Jade has an insane limited-time offer. Act now! #LuxuryInsurance",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "tier": "BRAND_POLICY",
                "category": "Fair Dealing",
                "severity": "HIGH",
                "message": "Aggressive sales pressure or countdown gimmicks.",
                "matched_phrase": "insane limited-time offer",
                "reference": "JA Assure Fair Dealing Policy"
            }]
        },
        cycle=2,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c2_2["id"],
        tag="off_brand_tone",
        note="Jade is a luxury private client brand; never advertise 'cheap' rates or 'insane offers'.",
        db_path=str(target_path),
    )

    # C2 Item 3 (DoctorShield - FAIL / REJECTED)
    c2_3 = models.insert_content(
        brand="DoctorShield",
        platform="Instagram",
        content_type="post",
        topic="Surgical malpractice protection",
        content="Surgeons: 100% immune from malpractice inquiries with DoctorShield. Don't risk your clinic! 🩺",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "NO_UNQUALIFIED_IMMUNITY",
                "tier": "REGULATORY",
                "category": "Absolute Immunity",
                "severity": "CRITICAL",
                "message": "Claims 100% immunity from disciplinary inquiries.",
                "matched_phrase": "100% immune",
                "reference": "Healthcare Advertising Code"
            }]
        },
        cycle=2,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c2_3["id"],
        tag="inaccurate_claim",
        note="Indemnity covers legal defense and claims, it does not confer statutory immunity.",
        db_path=str(target_path),
    )

    # C2 Item 4 (DoctorShield - FAIL / REJECTED)
    c2_4 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        topic="Flash offer for surgeons",
        content="Flash sale on surgeon malpractice insurance! Buy before midnight or lose everything. #MedTwitter",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "tier": "BRAND_POLICY",
                "category": "Medical Dignity",
                "severity": "HIGH",
                "message": "Fearmongering and flash sale language.",
                "matched_phrase": "buy before midnight",
                "reference": "JA Assure Medical Dignity Policy"
            }]
        },
        cycle=2,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c2_4["id"],
        tag="too_salesy",
        note="Flash sales are completely unacceptable for medical professional indemnity.",
        db_path=str(target_path),
    )

    # C2 Item 5 (DoctorShield - PASS / APPROVED)
    c2_5 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        topic="Healthcare governance and legal defense counsel",
        content=(
            "Navigating modern healthcare governance requires specialized medico-legal defense counsel.\n\n"
            "DoctorShield offers comprehensive professional indemnity tailored for medical specialists and surgeons across Singapore and Malaysia.\n\n"
            "All indemnity limits and legal defense benefits are subject to policy terms, conditions, and underwriting schedule.\n\n"
            "Review your practitioner profile: doctorshield.com/advisory"
        ),
        compliance_result=c1_pass_comp,
        cycle=2,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c2_5["id"], db_path=str(target_path))

    # =========================================================================
    # CYCLE 3: Measurable Improvement (40% Rejection Rate — 2 Rejected, 3 Approved)
    # =========================================================================

    # C3 Item 1 (Jade - FAIL / REJECTED)
    c3_1 = models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        topic="Direct response jewelry safeguarding",
        content="Discover bespoke jewelry safeguarding with Jade. DM us 'DEAL' to get an instant quote!",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "tier": "BRAND_POLICY",
                "category": "Brand Persona",
                "severity": "HIGH",
                "message": "Mass-market DM deal CTA inconsistent with luxury wealth advisory.",
                "matched_phrase": "DM us 'DEAL'",
                "reference": "Jade Brand Persona Guidelines"
            }]
        },
        cycle=3,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c3_1["id"],
        tag="wrong_cta",
        note="DM 'DEAL' is too casual for Jade private client clientele. Direct to online advisory portal.",
        db_path=str(target_path),
    )

    # C3 Item 2 (DoctorShield - FAIL / REJECTED)
    c3_2 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        topic="Malpractice coverage scope without qualifiers",
        content="Healthcare practitioners: Comprehensive malpractice coverage covers every clinical dispute without exception.",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "QUALIFIED_COVERAGE_CLAIMS",
                "tier": "REGULATORY",
                "category": "Disclosure",
                "severity": "MODERATE",
                "message": "Missing regulatory qualifier 'subject to policy terms and conditions'.",
                "matched_phrase": "Missing regulatory qualifier",
                "reference": "Insurance Disclosure Requirements"
            }]
        },
        cycle=3,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c3_2["id"],
        tag="inaccurate_claim",
        note="Must include 'subject to policy terms and conditions'.",
        db_path=str(target_path),
    )

    # C3 Item 3 (Jade - PASS / APPROVED)
    c3_3 = models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        topic="Heirloom preservation precision",
        content=(
            "Every heirloom tells a generational story. Safeguarding it requires precision and discretion. ✨🛡️\n\n"
            "Jade provides bespoke advisory and tailored insurance coverage for fine jewelry collections.\n\n"
            "💎 Certified specialist appraisals\n💎 Structured claims handling\n\n"
            "Coverage is subject to policy terms and conditions.\n\n"
            "👉 Explore our private client collection via link in bio."
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c3_3["id"], db_path=str(target_path))

    # C3 Item 4 (DoctorShield - PASS / APPROVED)
    c3_4 = models.insert_content(
        brand="DoctorShield",
        platform="Instagram",
        content_type="post",
        topic="Physician professional defense and counsel",
        content=(
            "Dedicated care requires dependable professional defense. 🩺🛡️\n\n"
            "DoctorShield delivers specialized professional indemnity and medico-legal counsel for physicians.\n\n"
            "Indemnity benefits are subject to policy terms and conditions.\n\n"
            "👉 Consult our medical defense advisors via link in bio."
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c3_4["id"], db_path=str(target_path))

    # C3 Item 5 (Jade - PASS / APPROVED)
    c3_5 = models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        topic="Fine jewelry legacy advisory",
        content=(
            "Fine jewelry represents enduring legacy. Jade offers bespoke advisory and tailored asset coverage, subject to policy terms and conditions. jadeassure.com #LuxuryInsurance"
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c3_5["id"], db_path=str(target_path))

    # =========================================================================
    # CYCLE 4: High Accuracy (20% Rejection Rate — 1 Rejected, 4 Approved)
    # =========================================================================

    # C4 Item 1 (DoctorShield - FAIL / REJECTED)
    c4_1 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        topic="Casual doctor advisory tone test",
        content="DoctorShield: The coolest insurance for docs in town. Chill out while we handle your cases.",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "OFF_BRAND_TONE",
                "tier": "BRAND_POLICY",
                "category": "Brand Persona",
                "severity": "MODERATE",
                "message": "Overly casual, informal slang inconsistent with clinical medico-legal defense persona.",
                "matched_phrase": "coolest insurance for docs",
                "reference": "DoctorShield Brand Guidelines"
            }]
        },
        cycle=4,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.reject_content(
        c4_1["id"],
        tag="off_brand_tone",
        note="Keep tone dignified and clinical, not overly casual or colloquial.",
        db_path=str(target_path),
    )

    # C4 Item 2 (Jade - PASS / APPROVED)
    c4_2 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic="High-value luxury asset management and vault coverage",
        content=(
            "In high-value luxury asset management, transparency is paramount.\n\n"
            "Jade partners with premier jewelers and auction houses to structure discretionary vault and exhibition coverage. "
            "All policies are underwritten in accordance with MAS guidelines and subject to policy terms and conditions."
        ),
        compliance_result=c1_pass_comp,
        cycle=4,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c4_2["id"], db_path=str(target_path))

    # C4 Item 3 (DoctorShield - PASS / APPROVED)
    c4_3 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        topic="Clinical governance and retroactive malpractice liabilities",
        content=(
            "Clinical governance review: Managing retroactive malpractice liabilities.\n\n"
            "DoctorShield provides seasoned defense counsel and comprehensive indemnity schedules tailored for surgical specialists, subject to policy terms and conditions."
        ),
        compliance_result=c1_pass_comp,
        cycle=4,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c4_3["id"], db_path=str(target_path))

    # C4 Item 4 (Jade - PASS / APPROVED)
    c4_4 = models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        topic="Heritage preservation through certified valuation",
        content="Heritage preservation through certified valuation. Bespoke private client insurance for luxury collectors, subject to terms: jadeassure.com/vault #WealthPreservation",
        compliance_result=c1_pass_comp,
        cycle=4,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c4_4["id"], db_path=str(target_path))

    # C4 Item 5 (DoctorShield - PASS / SCHEDULED)
    c4_5 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        topic="Comprehensive medico-legal defense scheduling",
        content="Comprehensive medico-legal defense tailored for medical practitioners. Safeguard your practice with DoctorShield, subject to policy terms. doctorshield.com #MedTwitter",
        compliance_result=c1_pass_comp,
        cycle=4,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )
    models.approve_content(c4_5["id"], db_path=str(target_path))
    models.schedule_content(c4_5["id"], db_path=str(target_path))

    # =========================================================================
    # CYCLE 5: Active Demo Bench Items (Pending Human Review)
    # =========================================================================
    
    # Demo Pending Item 1: Jade with Compliance FAIL (Ready for Judge Reject demo!)
    models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        topic="How jewellery businesses protect high-value inventory",
        content=(
            "When safeguarding multi-generational wealth, standard insurance falls short.\n\n"
            "At Jade, we provide bespoke valuation and guaranteed payouts for high-value jewelry and luxury collections. "
            "Our private client solutions ensure your family's priceless heirlooms are 100% protected with instant payout guaranteed.\n\n"
            "Act now before your heritage is at risk. Connect with our private client team today.\n\n"
            "#WealthPreservation #LuxuryAssets #JadeAssure #BespokeProtection"
        ),
        compliance_result=c1_fail_comp,
        cycle=5,
        sources=jade_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )

    # Demo Pending Item 2: DoctorShield with Compliance PASS (Ready for Judge Approve demo!)
    models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        topic="Medical indemnity and malpractice defense for healthcare professionals",
        content=(
            "Navigating modern healthcare governance requires specialized medico-legal defense counsel.\n\n"
            "DoctorShield offers comprehensive professional indemnity tailored for medical specialists, surgeons, and general practitioners across Singapore and Malaysia.\n\n"
            "Key Clinical Governance Safeguards:\n"
            "• Dedicated 24/7 medico-legal incident advisory\n"
            "• Expert representation for SMC/MMC disciplinary proceedings\n"
            "• Retroactive defense cost coverage for prior clinical practice\n\n"
            "All indemnity limits, exclusions, and legal defense benefits are subject to policy terms, conditions, and underwriting schedule.\n\n"
            "Review your practitioner indemnity profile: doctorshield.com/advisory\n\n"
            "#MedicalIndemnity #HealthcareGovernance #DoctorShield #ClinicalRisk"
        ),
        compliance_result=c1_pass_comp,
        cycle=5,
        sources=ds_source,
        generation_mode="offline",
        model="offline-engine",
        status="pending",
        db_path=str(target_path),
    )

    # =========================================================================
    # Demo Leads Fixture (Only in Demo Database!)
    # =========================================================================
    demo_leads = [
        (
            "Novena Orthopaedic Practice Group",
            "enquiries@novenaortho.com.sg",
            "Clinics",
            "Singapore",
            92,
            "Specialized SMC-aligned retroactive medical indemnity and multi-surgeon procedural defense.",
            "demo_fixture",
            "https://www.ja-assure.com/resources.html",
            {"vertical_match": 25, "region_match": 20, "business_profile": 18, "insurance_relevance": 19, "public_info_quality": 10},
            "new",
        ),
        (
            "Laurent Haute Joaillerie Pte Ltd",
            "concierge@laurentfinegems.com",
            "Jewellers",
            "Singapore",
            88,
            "Commercial Jewellers Block coverage across vault, workshop, and high-value transit.",
            "demo_fixture",
            "https://www.ja-assure.com/resources.html",
            {"vertical_match": 25, "region_match": 20, "business_profile": 16, "insurance_relevance": 17, "public_info_quality": 10},
            "new",
        ),
        (
            "Apex Medical Group Clinics",
            "info@apexmedical.my",
            "Clinics",
            "Malaysia",
            85,
            "Group practice professional indemnity covering clinical dispute financing and disciplinary defense.",
            "demo_fixture",
            "https://www.ja-assure.com/resources.html",
            {"vertical_match": 25, "region_match": 17, "business_profile": 16, "insurance_relevance": 17, "public_info_quality": 10},
            "contacted",
        ),
        (
            "Heritage Diamond Merchants SG",
            "vault@heritagediamonds.sg",
            "Jewellers",
            "Singapore",
            79,
            "Specie and wholesale diamond inventory block coverage with Lloyd's syndicate underwriting.",
            "demo_fixture",
            "https://www.ja-assure.com/resources.html",
            {"vertical_match": 25, "region_match": 20, "business_profile": 12, "insurance_relevance": 14, "public_info_quality": 8},
            "contacted",
        ),
        (
            "Aesthetic Medical Specialists Centre",
            "clinical@aestheticmd.com",
            "Clinics",
            "Singapore",
            74,
            "Specialist procedural dispute representation and clinical governance advisory.",
            "demo_fixture",
            "https://www.ja-assure.com/resources.html",
            {"vertical_match": 25, "region_match": 20, "business_profile": 10, "insurance_relevance": 11, "public_info_quality": 8},
            "new",
        ),
    ]

    for name, contact, vertical, region, fit_score, outreach, src, src_url, breakdown, status in demo_leads:
        models.insert_lead(
            name=name,
            contact=contact,
            vertical=vertical,
            region=region,
            fit_score=fit_score,
            outreach_draft=outreach,
            source=src,
            source_url=src_url,
            scoring_breakdown=breakdown,
            status=status,
            db_path=str(target_path),
        )

    print("[Seed] Demo seeding complete! Successfully created in demo database:")
    print("  • 20 historical review items across Cycles 1-4 (80% -> 60% -> 40% -> 20% rejection rate)")
    print("  • 2 active pending items for live demo (1 FAIL, 1 PASS)")
    print("  • 10 feedback records linked to rejected items")
    print("  • 5 prospective InsurTech leads (P1)")


if __name__ == "__main__":
    seed_data()
