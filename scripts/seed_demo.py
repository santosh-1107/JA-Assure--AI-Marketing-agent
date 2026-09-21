"""
Demo Seeding Script for JA Assure AI Marketing Agent.
Populates SQLite with multi-cycle InsurTech records demonstrating:
1. Downward rejection rate trend (80% -> 60% -> 40% -> 20%) backed by real rows.
2. Distinct brand voices (Jade vs. DoctorShield).
3. Before / After regeneration evidence with linked parent_ids.
4. Pending items ready for the live hackathon demonstration.
5. High-scoring InsurTech leads (P1).
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db, get_connection
from backend import models

def seed_data():
    print("Initializing fresh SQLite database...")
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing demo records to ensure clean reproducible demo state
    cursor.execute("DELETE FROM feedback;")
    cursor.execute("DELETE FROM content_queue;")
    cursor.execute("DELETE FROM leads;")
    conn.commit()
    conn.close()

    print("Seeding multi-cycle marketing review data...")

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
                "message": "The content claims guaranteed claim payouts. Insurance regulations require clarifying settlements depend on underwriting review.",
                "matched_phrase": "guaranteed payouts"
            },
            {
                "rule": "NO_GUARANTEED_PROTECTION",
                "tier": "REGULATORY",
                "category": "Regulatory Prohibition on Absolute Protection",
                "message": "The content uses absolute protection terminology ('100% protected').",
                "matched_phrase": "100% protected"
            }
        ]
    }
    c1_1 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=(
            "When safeguarding multi-generational wealth, standard insurance falls short.\n\n"
            "At Jade, we provide bespoke valuation and guaranteed payouts for high-value jewelry collections. "
            "Our private client solutions ensure your family's priceless heirlooms are 100% protected with instant payout guaranteed.\n\n"
            "Act now before your heritage is at risk. Connect with our private client team today."
        ),
        compliance_result=c1_fail_comp,
        cycle=1,
        status="rejected"
    )
    models.reject_content(
        c1_1["id"],
        tag="inaccurate_claim",
        note="Insurance regulatory standards prohibit promising guaranteed claim payouts or claiming 100% protection without policy qualifiers."
    )

    # C1 Item 2 (DoctorShield - FAIL / REJECTED)
    ds_c1_comp = {
        "status": "fail",
        "reasons": [
            {
                "rule": "NO_GUARANTEED_LEGAL_OUTCOME",
                "category": "Legal & Regulatory Prohibition",
                "message": "Prohibits guaranteeing court dismissal or zero malpractice liability.",
                "matched_phrase": "guaranteed dismissal"
            },
            {
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "category": "Professional Medical Dignity",
                "message": "Sensationalist scare tactics targeting physicians.",
                "matched_phrase": "patients will sue you tomorrow"
            }
        ]
    }
    c1_2 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content=(
            "Clinical practice faces unprecedented legal scrutiny across Southeast Asia.\n\n"
            "DoctorShield provides medical practitioners with guaranteed dismissal of patient malpractice claims and zero risk of disciplinary action.\n\n"
            "Patients will sue you tomorrow if you don't act fast. Protect your license immediately."
        ),
        compliance_result=ds_c1_comp,
        cycle=1,
        status="rejected"
    )
    models.reject_content(
        c1_2["id"],
        tag="inaccurate_claim",
        note="Never guarantee legal case dismissals and eliminate fearmongering phrases like 'patients will sue you tomorrow'."
    )

    # C1 Item 3 (Jade - FAIL / REJECTED)
    c1_3 = models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        content=(
            "Priceless jewelry deserves more than ordinary insurance! ✨💎\n\n"
            "Jade delivers bespoke protection with guaranteed payouts on every fine art and jewelry collection. "
            "100% protected, zero risk. Never worry about claim disputes again!\n\n"
            "👉 Tap link in bio now!"
        ),
        compliance_result=c1_fail_comp,
        cycle=1,
        status="rejected"
    )
    models.reject_content(
        c1_3["id"],
        tag="inaccurate_claim",
        note="Avoid 'zero risk' and 'guaranteed payouts' on Instagram lifestyle posts."
    )

    # C1 Item 4 (DoctorShield - FAIL / REJECTED)
    c1_4 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        content=(
            "Doctors: Patients will sue you tomorrow without indemnity. DoctorShield offers guaranteed dismissal and 100% protection. #MedTwitter"
        ),
        compliance_result=ds_c1_comp,
        cycle=1,
        status="rejected"
    )
    models.reject_content(
        c1_4["id"],
        tag="too_salesy",
        note="Tone down aggressive threat headlines on X. Emphasize calm medico-legal advisory."
    )

    # C1 Item 5 (Jade - PASS / APPROVED)
    c1_pass_comp = {"status": "pass", "reasons": []}
    c1_5 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=(
            "Safeguarding multi-generational heirlooms requires more than standard coverage.\n\n"
            "At Jade, our bespoke policies offer private client valuation and structured claims assessment — subject to policy terms and underwriter schedule.\n\n"
            "Connect with our advisory desk: jadeassure.com/bespoke"
        ),
        compliance_result=c1_pass_comp,
        cycle=1,
        status="approved"
    )

    # =========================================================================
    # CYCLE 2: Learning Applied (60% Rejection Rate — 3 Rejected, 2 Approved)
    # =========================================================================

    # C2 Item 1 (Jade - Regenerated from C1 Item 1! BEFORE/AFTER SHOWCASE)
    c2_1 = models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
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
        status="approved"
    )

    # C2 Item 2 (Jade - FAIL / REJECTED)
    c2_2 = models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        content="Looking for the cheapest luxury jewelry insurance in Singapore? Jade has an insane limited-time offer. Act now! #LuxuryInsurance",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "category": "Fair Dealing",
                "message": "Aggressive sales pressure or countdown gimmicks.",
                "matched_phrase": "insane limited-time offer"
            }]
        },
        cycle=2,
        status="rejected"
    )
    models.reject_content(
        c2_2["id"],
        tag="off_brand_tone",
        note="Jade is a luxury private client brand; never advertise 'cheap' rates or 'insane offers'."
    )

    # C2 Item 3 (DoctorShield - FAIL / REJECTED)
    c2_3 = models.insert_content(
        brand="DoctorShield",
        platform="Instagram",
        content_type="post",
        content="Surgeons: 100% immune from malpractice inquiries with DoctorShield. Don't risk your clinic! 🩺",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "NO_UNQUALIFIED_IMMUNITY",
                "category": "Absolute Immunity",
                "message": "Claims 100% immunity from disciplinary inquiries.",
                "matched_phrase": "100% immune"
            }]
        },
        cycle=2,
        status="rejected"
    )
    models.reject_content(
        c2_3["id"],
        tag="inaccurate_claim",
        note="Indemnity covers legal defense and claims, it does not confer statutory immunity."
    )

    # C2 Item 4 (DoctorShield - FAIL / REJECTED)
    c2_4 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        content="Flash sale on surgeon malpractice insurance! Buy before midnight or lose everything. #MedTwitter",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "INAPPROPRIATE_SALES_LANGUAGE",
                "category": "Medical Dignity",
                "message": "Fearmongering and flash sale language.",
                "matched_phrase": "buy before midnight"
            }]
        },
        cycle=2,
        status="rejected"
    )
    models.reject_content(
        c2_4["id"],
        tag="too_salesy",
        note="Flash sales are completely unacceptable for medical professional indemnity."
    )

    # C2 Item 5 (DoctorShield - PASS / APPROVED)
    c2_5 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content=(
            "Navigating modern healthcare governance requires specialized medico-legal defense counsel.\n\n"
            "DoctorShield offers comprehensive professional indemnity tailored for medical specialists and surgeons across Singapore and Malaysia.\n\n"
            "All indemnity limits and legal defense benefits are subject to policy terms, conditions, and underwriting schedule.\n\n"
            "Review your practitioner profile: doctorshield.com/advisory"
        ),
        compliance_result=c1_pass_comp,
        cycle=2,
        status="approved"
    )

    # =========================================================================
    # CYCLE 3: Measurable Improvement (40% Rejection Rate — 2 Rejected, 3 Approved)
    # =========================================================================

    # C3 Item 1 (Jade - FAIL / REJECTED)
    c3_1 = models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        content="Discover bespoke jewelry safeguarding with Jade. DM us 'DEAL' to get an instant quote!",
        compliance_result=c1_pass_comp,
        cycle=3,
        status="rejected"
    )
    models.reject_content(
        c3_1["id"],
        tag="wrong_cta",
        note="DM 'DEAL' is too casual for Jade private client clientele. Direct to online advisory portal."
    )

    # C3 Item 2 (DoctorShield - FAIL / REJECTED)
    c3_2 = models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        content="Healthcare practitioners: Comprehensive malpractice coverage covers every clinical dispute without exception.",
        compliance_result={
            "status": "fail",
            "reasons": [{
                "rule": "QUALIFIED_COVERAGE_CLAIMS",
                "category": "Disclosure",
                "message": "Missing regulatory qualifier 'subject to policy terms and conditions'.",
                "matched_phrase": "Missing regulatory qualifier"
            }]
        },
        cycle=3,
        status="rejected"
    )
    models.reject_content(
        c3_2["id"],
        tag="inaccurate_claim",
        note="Must include 'subject to policy terms and conditions'."
    )

    # C3 Item 3 (Jade - PASS / APPROVED)
    models.insert_content(
        brand="Jade",
        platform="Instagram",
        content_type="post",
        content=(
            "Every heirloom tells a generational story. Safeguarding it requires precision and discretion. ✨🛡️\n\n"
            "Jade provides bespoke advisory and tailored insurance coverage for fine jewelry collections.\n\n"
            "💎 Certified specialist appraisals\n💎 Structured claims handling\n\n"
            "Coverage is subject to policy terms and conditions.\n\n"
            "👉 Explore our private client collection via link in bio."
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        status="approved"
    )

    # C3 Item 4 (DoctorShield - PASS / APPROVED)
    models.insert_content(
        brand="DoctorShield",
        platform="Instagram",
        content_type="post",
        content=(
            "Dedicated care requires dependable professional defense. 🩺🛡️\n\n"
            "DoctorShield delivers specialized professional indemnity and medico-legal counsel for physicians.\n\n"
            "Indemnity benefits are subject to policy terms and conditions.\n\n"
            "👉 Consult our medical defense advisors via link in bio."
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        status="approved"
    )

    # C3 Item 5 (Jade - PASS / APPROVED)
    models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        content=(
            "Fine jewelry represents enduring legacy. Jade offers bespoke advisory and tailored asset coverage, subject to policy terms and conditions. jadeassure.com #LuxuryInsurance"
        ),
        compliance_result=c1_pass_comp,
        cycle=3,
        status="approved"
    )

    # =========================================================================
    # CYCLE 4: High Accuracy (20% Rejection Rate — 1 Rejected, 4 Approved)
    # =========================================================================

    # C4 Item 1 (DoctorShield - FAIL / REJECTED)
    c4_1 = models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content="DoctorShield: The coolest insurance for docs in town. Chill out while we handle your cases.",
        compliance_result=c1_pass_comp,
        cycle=4,
        status="rejected"
    )
    models.reject_content(
        c4_1["id"],
        tag="off_brand_tone",
        note="Keep tone dignified and clinical, not overly casual or colloquial."
    )

    # C4 Item 2 (Jade - PASS / APPROVED)
    models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=(
            "In high-value luxury asset management, transparency is paramount.\n\n"
            "Jade partners with premier jewelers and auction houses to structure discretionary vault and exhibition coverage. "
            "All policies are underwritten in accordance with MAS guidelines and subject to policy terms and conditions."
        ),
        compliance_result=c1_pass_comp,
        cycle=4,
        status="approved"
    )

    # C4 Item 3 (DoctorShield - PASS / APPROVED)
    models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
        content=(
            "Clinical governance review: Managing retroactive malpractice liabilities.\n\n"
            "DoctorShield provides seasoned defense counsel and comprehensive indemnity schedules tailored for surgical specialists, subject to policy terms and conditions."
        ),
        compliance_result=c1_pass_comp,
        cycle=4,
        status="approved"
    )

    # C4 Item 4 (Jade - PASS / APPROVED)
    models.insert_content(
        brand="Jade",
        platform="X",
        content_type="tweet",
        content="Heritage preservation through certified valuation. Bespoke private client insurance for luxury collectors, subject to terms: jadeassure.com/vault #WealthPreservation",
        compliance_result=c1_pass_comp,
        cycle=4,
        status="approved"
    )

    # C4 Item 5 (DoctorShield - PASS / SCHEDULED)
    models.insert_content(
        brand="DoctorShield",
        platform="X",
        content_type="tweet",
        content="Comprehensive medico-legal defense tailored for medical practitioners. Safeguard your practice with DoctorShield, subject to policy terms. doctorshield.com #MedTwitter",
        compliance_result=c1_pass_comp,
        cycle=4,
        status="scheduled"
    )

    # =========================================================================
    # CYCLE 5: Active Demo Bench Items (Pending Human Review)
    # =========================================================================
    
    # Demo Pending Item 1: Jade with Compliance FAIL (Ready for Judge Reject demo!)
    models.insert_content(
        brand="Jade",
        platform="LinkedIn",
        content_type="post",
        content=(
            "When safeguarding multi-generational wealth, standard insurance falls short.\n\n"
            "At Jade, we provide bespoke valuation and guaranteed payouts for high-value jewelry and luxury collections. "
            "Our private client solutions ensure your family's priceless heirlooms are 100% protected with instant payout guaranteed.\n\n"
            "Act now before your heritage is at risk. Connect with our private client team today.\n\n"
            "#WealthPreservation #LuxuryAssets #JadeAssure #BespokeProtection"
        ),
        compliance_result=c1_fail_comp,
        cycle=5,
        status="pending"
    )

    # Demo Pending Item 2: DoctorShield with Compliance PASS (Ready for Judge Approve demo!)
    models.insert_content(
        brand="DoctorShield",
        platform="LinkedIn",
        content_type="post",
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
        status="pending"
    )

    # =========================================================================
    # P1 Feature: High-Scoring InsurTech Leads
    # =========================================================================
    leads_data = [
        (
            "Dr. Marcus Tan, Senior Orthopaedic Surgeon",
            "marcus.tan@novenaortho.com.sg",
            "Clinics",
            92,
            "Dear Dr. Tan, given your surgical caseload at Novena, we noticed recent shifts in SMC indemnity requirements. DoctorShield provides retroactive indemnity and specialized defense counsel tailored for orthopaedic specialists. Would you be open to a brief peer review of your coverage?",
            "new"
        ),
        (
            "Sophia Laurent, Laurent & Co. Haute Joaillerie",
            "sophia@laurentfinegems.com",
            "Jewellers",
            88,
            "Dear Ms. Laurent, fine jewelers managing multi-carat bespoke pieces require more than commercial property insurance. Jade provides bespoke discretionary underwriting and vault transit coverage across Singapore and Hong Kong. We would welcome the chance to share our jeweler partnership advisory.",
            "new"
        ),
        (
            "Apex Medical Group (4 GP Clinics)",
            "admin@apexmedical.my",
            "Clinics",
            85,
            "Dear Clinical Directors, group practice indemnity requires seamless cross-practitioner coverage without gaps in retroactive defense dates. DoctorShield offers tailored multi-clinician defense packages.",
            "contacted"
        ),
        (
            "Heritage Diamond Vaults Singapore",
            "curator@heritagediamonds.sg",
            "Jewellers",
            79,
            "Dear Curator, Jade's private client vault coverage is crafted specifically for certified natural diamonds and private collections, backed by specialized underwriting.",
            "qualified"
        ),
        (
            "Dr. Rachel Lim, Aesthetics & Dermatology",
            "rachel.lim@aestheticmd.com",
            "Clinics",
            74,
            "Dear Dr. Lim, aesthetic medical disputes carry unique procedural scrutiny. DoctorShield provides 24/7 medico-legal incident guidance and defense representation.",
            "new"
        ),
    ]

    for name, contact, vertical, fit_score, outreach, status in leads_data:
        models.insert_lead(
            name=name,
            contact=contact,
            vertical=vertical,
            fit_score=fit_score,
            outreach_draft=outreach,
            status=status,
        )

    print("Seeding complete! Successfully created:")
    print("  • 20 historical review items across Cycles 1-4 (80% -> 60% -> 40% -> 20% rejection rate)")
    print("  • 2 active pending items for live demo (1 FAIL, 1 PASS)")
    print("  • 10 feedback records linked to rejected items")
    print("  • 5 prospective InsurTech leads (P1)")

if __name__ == "__main__":
    seed_data()
