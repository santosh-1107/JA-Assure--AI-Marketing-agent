"""
Generate official authoritative JA Assure seed PDF documents.
Places multi-page PDFs with rich insurance domain content in data/knowledge/pdfs/.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "pdfs"


def create_jewellers_block_pdf(output_path: Path):
    """Generate official JA Assure Jewellers Block & Specie Insurance Guide (4 pages)."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1B365D'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#D4AF37'),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=8,
    )

    story = []

    # PAGE 1: Overview & Scope of Jewellers Block Coverage
    story.append(Paragraph("JA Assure — Jade Jewellers Block & Specie Insurance", title_style))
    story.append(Paragraph("Official Product Disclosure and Underwriting Guidelines (Page 1)", h2_style))
    story.append(Paragraph(
        "JA Assure provides specialized InsurTech solutions for high-value luxury assets. Jade is JA Assure's dedicated "
        "brand delivering comprehensive Jewellers Block and Specie insurance across Southeast Asia, including Singapore, "
        "Malaysia, and Hong Kong. Standard commercial property insurance policies routinely exclude precious metals, loose gemstones, "
        "and high-value retail inventory due to inherent theft and transit hazards.",
        body_style
    ))
    story.append(Paragraph(
        "Jade Jewellers Block covers all risks of physical loss or damage to diamond collections, gold jewellery, "
        "watches, and loose stones, except as specifically excluded in the policy schedule. Coverage is strictly subject "
        "to detailed inventory appraisal and verified security criteria.",
        body_style
    ))
    story.append(Paragraph("Key Coverage Pillars:", h2_style))
    story.append(Paragraph("1. Retail Stock & Display Premises: Physical loss or damage to stock on retail premises during operating hours.", body_style))
    story.append(Paragraph("2. Safe & Vault Custody: Overnight protection for inventory securely locked within approved Class 1 to Class 5 safes.", body_style))
    story.append(Paragraph("3. Transit & Armoured Courier: Protection during registered transit, secure logistics, and exhibition movement.", body_style))
    story.append(Paragraph("4. Entrustment & Memorandum: Coverage while jewellery is entrusted to certified cutters, polishers, or third-party dealers.", body_style))

    story.append(PageBreak())

    # PAGE 2: Underwriting Security Requirements & Safe Specifications
    story.append(Paragraph("Jade Jewellers Block — Security Warranties & Safe Criteria (Page 2)", title_style))
    story.append(Paragraph("Mandatory Safe Specifications & Warranties", h2_style))
    story.append(Paragraph(
        "Underwriting protection requires strict adherence to physical and electronic security warranties. "
        "Overnight stock storage must meet JA Assure risk engineering benchmarks:",
        body_style
    ))
    story.append(Paragraph(
        "• Safe Classification: Safes must possess UL TL-15, TL-30, or EN 1143-1 Grade III or higher certification. "
        "Safes weighing under 1,000 kilograms must be structurally anchored into reinforced concrete floors.",
        body_style
    ))
    story.append(Paragraph(
        "• Dual Custody & Time Lock: Vaults holding inventory exceeding SGD 2,000,000 must feature dual-combination locks "
        "and electronic time-lock mechanisms active outside retail business hours.",
        body_style
    ))
    story.append(Paragraph(
        "• 24/7 Monitored Central Alarm (CMS): Direct line or dual-path 4G/IP signalling to an approved central alarm monitoring station. "
        "Line-tamper detection and seismic vibration sensors on all vault perimeters are mandatory underwriting conditions.",
        body_style
    ))
    story.append(Paragraph(
        "• CCTV Surveillance: High-definition closed-circuit cameras recording 30 days of continuous footage covering all entrances, "
        "display counters, and the vault perimeter.",
        body_style
    ))

    story.append(PageBreak())

    # PAGE 3: Transit, Exhibition, and International Shipping Provisions
    story.append(Paragraph("Jade Jewellers Block — Transit, Exhibition & Memorandum (Page 3)", title_style))
    story.append(Paragraph("Armoured Logistics and Overseas Fair Extensions", h2_style))
    story.append(Paragraph(
        "High-value jewellery inventory is at peak risk during transit between ateliers, gemmological laboratories, "
        "and international luxury trade fairs (e.g. Hong Kong Jewellery & Gem Fair, Baselworld). Jade provides bespoke "
        "transit endorsements subject to the following underwriting protocols:",
        body_style
    ))
    story.append(Paragraph(
        "• Approved Armoured Couriers: Shipments exceeding SGD 100,000 must be conveyed via approved specialized logistics "
        "providers (e.g. Malca-Amit, Brink's, Ferrari Logistics) with armoured escort and barcode telemetry.",
        body_style
    ))
    story.append(Paragraph(
        "• Hand-Carry Regulations: Hand-carry by vetted full-time directors is permitted up to endorsed limits (maximum SGD 500,000) "
        "provided items remain in personal custody at all times and are never checked into aircraft baggage holds.",
        body_style
    ))
    story.append(Paragraph(
        "• Exhibition Warranty: At trade shows, items removed from display cases for prospective client inspection must be "
        "handled by authorized staff with continuous line-of-sight supervision.",
        body_style
    ))

    story.append(PageBreak())

    # PAGE 4: Policy Exclusions, Claim Procedures & Anti-Hallucination Disclosures
    story.append(Paragraph("Jade Jewellers Block — Exclusions & Claim Disclosures (Page 4)", title_style))
    story.append(Paragraph("Standard Policy Exclusions & Regulatory Disclosures", h2_style))
    story.append(Paragraph(
        "To ensure compliance with Monetary Authority of Singapore (MAS) and regional insurance standards, "
        "JA Assure explicitly outlines standard policy exclusions. No policy guarantees unconditional claims settlement.",
        body_style
    ))
    story.append(Paragraph(
        "Standard Policy Exclusions include:\n"
        "1. Mysterious Disappearance: Unexplained inventory shortages discovered solely during routine annual stock audits.\n"
        "2. Dishonesty of Employees: Fidelity theft unless specifically endorsed with an approved commercial crime extension.\n"
        "3. Wear, Tear & Gradual Deterioration: Inherent vice, atmospheric conditions, or faulty repair work.\n"
        "4. Unattended Vehicles: Loss of jewellery left inside any unattended motor vehicle is strictly excluded without exception.\n"
        "5. War, Terrorism & Nuclear Contamination: Statutory exclusions applied across all standard Lloyd's and regional syndicate binders.",
        body_style
    ))
    story.append(Paragraph(
        "Important Regulatory Notice: Jade is an insurance technology advisory platform under JA Assure. "
        "All terms, coverage limits, sub-limits, and claims assessments are strictly subject to policy wording, underwriter schedules, "
        "and individual risk survey approval. Never promise 100% protection or guaranteed payouts.",
        body_style
    ))

    doc.build(story)
    print(f"Generated Jewellers Block PDF at: {output_path}")


def create_doctorshield_pdf(output_path: Path):
    """Generate official DoctorShield Medical Malpractice & Indemnity Guide (3 pages)."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#004D40'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#26A69A'),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=8,
    )

    story = []

    # PAGE 1: Overview & Scope of Medical Indemnity
    story.append(Paragraph("JA Assure — DoctorShield Medical Malpractice Indemnity", title_style))
    story.append(Paragraph("Clinical Risk Governance and Professional Indemnity (Page 1)", h2_style))
    story.append(Paragraph(
        "DoctorShield is JA Assure's premier medical indemnity and professional liability platform, serving medical practitioners, "
        "dental surgeons, specialists, and private clinics across Malaysia and Singapore. "
        "In modern clinical practice, doctors face increasing legal exposure from patient negligence claims, statutory inquiries, "
        "and medical council disciplinary hearings (e.g. Singapore Medical Council, Malaysian Medical Council).",
        body_style
    ))
    story.append(Paragraph(
        "DoctorShield delivers contractual claims-made indemnity protection. Unlike discretionary indemnity organizations "
        "which may refuse defense at board discretion, DoctorShield provides enforceable contractual defense backed by "
        "leading A-rated insurers.",
        body_style
    ))
    story.append(Paragraph("Core Protection Scope:", h2_style))
    story.append(Paragraph("• Clinical Negligence Defense: Legal defense costs for civil malpractice claims arising from medical treatment.", body_style))
    story.append(Paragraph("• Statutory & Medical Council Inquiries: Coverage for legal representation during Medical Council disciplinary hearings and coroners' inquests.", body_style))
    story.append(Paragraph("• Defamation & Good Samaritan Acts: Protection extending to emergency medical aid rendered outside clinic premises.", body_style))
    story.append(Paragraph("• Run-off & Retirement Cover: Extended reporting period options for retired or transitioning practitioners.", body_style))

    story.append(PageBreak())

    # PAGE 2: Claims Process, Legal Representation & Panel Counsel
    story.append(Paragraph("DoctorShield — Claims Handling & Panel Counsel (Page 2)", title_style))
    story.append(Paragraph("Disciplined Legal Defense and Incident Reporting", h2_style))
    story.append(Paragraph(
        "A critical advantage of DoctorShield is rapid appointment of specialist medico-legal defense counsel. "
        "Early intervention mitigates reputation damage and ensures procedural rights are protected before medical boards.",
        body_style
    ))
    story.append(Paragraph(
        "• Independent Specialist Panel: Access to experienced medical defense litigators with proven clinical law expertise in ASEAN.",
        body_style
    ))
    story.append(Paragraph(
        "• Prompt Incident Notification: Insured doctors must notify DoctorShield upon receiving any solicitor notice, patient complaint letter, "
        "or Medical Council query. Prompt reporting preserves coverage under claims-made triggers.",
        body_style
    ))
    story.append(Paragraph(
        "• Consent to Settle Clause: Settlement of clinical disputes is conducted in close consultation with the doctor, "
        "protecting professional clinical reputation and avoiding unwarranted fault admissions.",
        body_style
    ))

    story.append(PageBreak())

    # PAGE 3: Exclusions, Ethical Bounds & Regulatory Warnings
    story.append(Paragraph("DoctorShield — Exclusions & Ethical Disclosures (Page 3)", title_style))
    story.append(Paragraph("Regulatory Disclosures & Excluded Acts", h2_style))
    story.append(Paragraph(
        "In compliance with healthcare advertising guidelines and insurance regulations, DoctorShield marketing must never "
        "use scare tactics or promise lawsuit dismissals.",
        body_style
    ))
    story.append(Paragraph(
        "Standard Policy Exclusions:\n"
        "1. Criminal, Fraudulent or Malicious Acts: Coverage does not defend intentional criminal conduct or fraudulent billing.\n"
        "2. Practice Outside Endorsed Specialty: Performing advanced surgical or aesthetic procedures outside approved registered qualifications.\n"
        "3. Prior Known Incidents: Circumstances known to the physician prior to policy inception that were not disclosed.\n"
        "4. Fines & Penalties: Statutory criminal fines or punitive sanctions imposed by regulatory bodies.",
        body_style
    ))
    story.append(Paragraph(
        "Regulatory Notice: DoctorShield is an insurance advisory solution provided through JA Assure. "
        "Legal defense and indemnity limits are subject to underwriting acceptance, specialty risk tiering, "
        "and policy terms. Marketing must avoid sensationalism or fearmongering.",
        body_style
    ))

    doc.build(story)
    print(f"Generated DoctorShield PDF at: {output_path}")


def create_corporate_architecture_pdf(output_path: Path):
    """Generate official JA Assure Corporate Architecture & Insurance Foundations Guide (3 pages)."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1B365D'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#D4AF37'),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=8,
    )

    story = []

    # PAGE 1: Foundations of Uncertainty & Risk Pooling
    story.append(Paragraph("JA Assure — The Architecture of Uncertainty", title_style))
    story.append(Paragraph("Foundations of Risk Pooling and InsurTech Innovation (Page 1)", h2_style))
    story.append(Paragraph(
        "JA Assure is an InsurTech ecosystem operating across Southeast Asia with its regional hub in Singapore. "
        "Insurance in its purest form is the architecture of uncertainty: a collective social and economic mechanism "
        "designed to transform catastrophic personal volatility into manageable, pooled risk.",
        body_style
    ))
    story.append(Paragraph(
        "Through disciplined risk engineering, verified underwriting criteria, and real-time digital policy issuance, "
        "JA Assure bridges specialized market sectors — such as luxury jewellery assets (Jade) and healthcare practitioners (DoctorShield) — "
        "with institutional reinsurance and international underwriting syndicates.",
        body_style
    ))

    story.append(PageBreak())

    # PAGE 2: The Insurance Ecosystem & Capital Flows
    story.append(Paragraph("JA Assure — The Insurance Ecosystem (Page 2)", title_style))
    story.append(Paragraph("How Risk and Premiums Flow Across The Value Chain", h2_style))
    story.append(Paragraph(
        "The insurance ecosystem relies on multi-layered capital protection: primary insured clients pay premiums into actuarially "
        "calibrated risk pools managed by licensed underwriters. Excess and catastrophic risks are ceded to global reinsurers. "
        "JA Assure provides the digital operating layer that orchestrates risk assessment, documentation, and compliance verification.",
        body_style
    ))
    story.append(Paragraph(
        "Core Operating Principles:\n"
        "• Actuarial Soundness: Premiums reflect true underlying risk rather than speculative marketing discounts.\n"
        "• Utmost Good Faith (Uberrimae Fidei): Transparent disclosure between insureds, advisory agents, and underwriters.\n"
        "• Contractual Certainty: Enforceable insurance contracts governed by territorial insurance acts.",
        body_style
    ))

    story.append(PageBreak())

    # PAGE 3: Anti-Hallucination & Governance Mandate
    story.append(Paragraph("JA Assure — Corporate Governance & Marketing Mandate (Page 3)", title_style))
    story.append(Paragraph("Compliance Guidelines for Marketing Intelligence & AI Communications", h2_style))
    story.append(Paragraph(
        "JA Assure enforces a zero-tolerance policy against deceptive insurance marketing. "
        "All customer-facing communications must adhere to statutory advertising rubrics:",
        body_style
    ))
    story.append(Paragraph(
        "1. No Unsubstantiated Superlatives: Never claim to be the '#1 insurer' or 'cheapest provider' without documented regulatory proof.\n"
        "2. No Guaranteed Settlements: All claims are subject to independent loss adjusters and policy definitions.\n"
        "3. Mandatory Qualifier Disclosure: Every marketing asset must cite that terms and conditions apply.\n"
        "4. Competitor Intelligence Boundaries: Public competitor messaging may be referenced for positioning contrast only, "
        "and must never be treated as authoritative underwriting evidence for JA Assure products.",
        body_style
    ))

    doc.build(story)
    print(f"Generated Corporate Architecture PDF at: {output_path}")


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    create_jewellers_block_pdf(PDF_DIR / "JA_Assure_Jewellers_Block_Guide.pdf")
    create_doctorshield_pdf(PDF_DIR / "DoctorShield_Medical_Indemnity_Governance.pdf")
    create_corporate_architecture_pdf(PDF_DIR / "JA_Assure_Corporate_Architecture.pdf")
    print(f"All 3 official JA Assure seed PDFs successfully generated in {PDF_DIR}")


if __name__ == "__main__":
    main()
