"""
Official JA Assure Knowledge Sources.
Grounding reference material extracted from https://www.ja-assure.com/resources.html.
Provides verified company facts, product definitions, and underwriting principles.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

KNOWLEDGE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"

OFFICIAL_RESOURCES: List[Dict[str, Any]] = [
    {
        "id": "jewellers_block",
        "title": "Jewellers Block and Specie Insurance: Protecting the World's Most Precious Assets",
        "url": "https://www.ja-assure.com/blog-jewellers-block.html",
        "brand": "Jade",
        "vertical": "Jewellery, Precious Metals, Gemstones & Specie",
        "keywords": [
            "jewellery", "jewellers block", "specie", "diamonds", "gold", "bullion",
            "vault", "transit", "high-value inventory", "exhibition", "consignment",
            "unattended vehicle", "gemstones", "appraisal", "precious assets"
        ],
        "summary": (
            "Jewellers Block insurance is an all-risks commercial policy specifically designed for businesses "
            "in the jewellery, precious metals, and gemstone trade. Unlike standard property insurance (which only covers "
            "premises) or marine cargo (which only covers transit), Jewellers Block covers stock in trade wherever it is "
            "located: on premises (showroom, vault, workshop), in transit, at trade exhibitions and fairs, with sales "
            "representatives, with third parties (for repair, setting, polishing), and in private residence vaults "
            "(common in Southeast Asia). It is strictly a commercial trade product for businesses, NOT retail consumer insurance. "
            "Specie is the broader category covering high-value portable property including bullion and cash in transit."
        ),
        "key_facts": [
            "Commercial trade coverage: covers businesses (manufacturers, wholesalers, retailers, diamond merchants), not individual retail consumers.",
            "Comprehensive block coverage: covers showroom, vault, transit, trade fairs/exhibitions, and third-party custody for repair/polishing.",
            "Private residence coverage: specially underwritten for family-owned jewellers in SE Asia where inventory is stored in home vaults overnight.",
            "Specie category: encompasses physical bullion, precious metals, and high-value negotiable assets.",
            "Key underwriting criteria: graded physical vaults/safes, 24/7 alarm & dual-path monitoring, transit security protocols, strict inventory records.",
            "Standard exclusion: unattended vehicle exclusion (theft from vehicles left without qualified security personnel is universally excluded)."
        ],
    },
    {
        "id": "medical_indemnity",
        "title": "Medical Indemnity Insurance: Why It Exists, Who It Really Protects, and How It Works",
        "url": "https://www.ja-assure.com/blog-medical-malpractice.html",
        "brand": "DoctorShield",
        "vertical": "Healthcare Professionals, Medical Specialists, Clinics & Surgeons",
        "keywords": [
            "medical indemnity", "medical malpractice", "professional liability", "physicians",
            "surgeons", "clinical risk", "legal defence", "patient safety", "disciplinary inquiries",
            "inquests", "claims-made", "retroactive date", "healthcare governance"
        ],
        "summary": (
            "Medical malpractice and professional indemnity insurance serves a dual function: first, litigation financing "
            "to fund specialized medico-legal defense, medical expert analysis, and procedural costs when a clinical dispute occurs; "
            "second, financial means to provide fair compensation to patients when the standard of care is breached. "
            "JA Assure frames medical indemnity fundamentally as a patient safety and healthcare governance mechanism, "
            "rather than just doctor immunity. Operating on a claims-made basis, coverage requires maintaining a continuous "
            "retroactive date covering prior clinical acts."
        ),
        "key_facts": [
            "Dual function: litigation defense financing (expert witnesses, legal representation) and patient compensation funding.",
            "Patient safety mechanism: ensures legitimate claims are adjudicated with financial backing rather than adversarial denial.",
            "Claims-made structure: policy in force at the time the claim is made responds, provided the incident occurred after the retroactive date.",
            "Disciplinary proceedings & inquests: covers legal representation at statutory medical council inquiries (e.g. SMC, MMC), not just court litigation.",
            "No guaranteed outcome: outcomes depend on evidence and standard-of-care assessment; indemnity cannot guarantee court verdict dismissal or immunity from investigation."
        ],
    },
    {
        "id": "architecture_uncertainty",
        "title": "The Architecture of Uncertainty: Defining Insurance and Its Guiding Principles",
        "url": "https://www.ja-assure.com/blog-architecture-uncertainty.html",
        "brand": "General",
        "vertical": "Insurance Fundamentals & Core Principles",
        "keywords": [
            "uncertainty", "risk pooling", "law of large numbers", "indemnity principle",
            "utmost good faith", "insurable interest", "proximate cause", "subrogation"
        ],
        "summary": (
            "Insurance is the mathematical conquest of uncertainty through risk pooling and the law of large numbers. "
            "Five fundamental legal principles govern all insurance contracts: 1. Utmost Good Faith (Uberrimae Fidei); "
            "2. Insurable Interest; 3. Indemnity (restoring the insured to their exact pre-loss position without enrichment); "
            "4. Proximate Cause; 5. Subrogation and Contribution preventing double recovery."
        ),
        "key_facts": [
            "Principle of Indemnity: insurance restores the policyholder to pre-loss state; it is never a vehicle for profit or guaranteed financial gain.",
            "Utmost Good Faith: policyholder must disclose all material facts regarding risk exposure.",
            "Risk pooling: diverse individual risks combined into a statistical collective."
        ],
    },
    {
        "id": "insurance_ecosystem",
        "title": "The Insurance Ecosystem: How Your Premium Travels From Policyholder to Reinsurer",
        "url": "https://www.ja-assure.com/blog-insurance-ecosystem.html",
        "brand": "General",
        "vertical": "Global Insurance Value Chain & Distribution",
        "keywords": [
            "insurance ecosystem", "premiums", "reinsurance", "lloyds", "syndicates",
            "managing general agents", "mga", "brokers", "retrocession"
        ],
        "summary": (
            "Traces the journey of premium capital across the global risk distribution hierarchy: direct retail brokers "
            "and InsurTech MGAs (like JA Assure), primary insurance carriers, Lloyd's of London syndicates, reinsurance giants, "
            "and retrocessionaires who protect the ultimate solvency of the financial system."
        ),
        "key_facts": [
            "Managing General Agents (MGAs): JA Assure acts as a specialized InsurTech MGA with delegated underwriting authority from global syndicates.",
            "Reinsurance backing: complex risks (Specie, Medical Malpractice) are supported by global treaty capacity.",
            "Risk transfer: premiums pool globally to absorb catastrophic single-event losses."
        ],
    },
    {
        "id": "world_of_insurance",
        "title": "The World of Insurance: Types, Classes, and the Technologies Reshaping the Industry",
        "url": "https://www.ja-assure.com/blog-world-insurance.html",
        "brand": "General",
        "vertical": "Specialty Lines & InsurTech Innovation",
        "keywords": [
            "specialty lines", "marine", "cyber", "specie", "parametric insurance",
            "insurtech", "ai underwriting", "iot risk tracking", "high-value transit"
        ],
        "summary": (
            "Surveys the diverse taxonomy of insurance: personal vs. commercial lines, standard casualty vs. complex "
            "specialty classes (Specie, Medical Malpractice, Cyber, High-Value Transit). Examines how digital APIs, "
            "automated quotation engines, and IoT monitoring are modernizing risk management across Southeast Asia."
        ),
        "key_facts": [
            "Specialty lines require bespoke underwriting rather than generic mass-market rating tables.",
            "Modern InsurTech platforms combine instant binding with strict underwriting risk controls.",
            "High-value transit and jewelry block require integrated physical and digital security assessments."
        ],
    },
]


def load_all_sources() -> List[Dict[str, Any]]:
    """Load sources from data/knowledge JSON files or return built-in official resources."""
    if KNOWLEDGE_DATA_DIR.exists():
        loaded = []
        for json_file in sorted(KNOWLEDGE_DATA_DIR.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded.append(data)
            except Exception:
                pass
        if loaded:
            return loaded
    return OFFICIAL_RESOURCES
