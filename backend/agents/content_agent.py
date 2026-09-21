"""
Content Agent for JA Assure AI Marketing Agent.
Generates platform- and brand-tailored marketing assets.
Incorporates human feedback as few-shot constraints into prompts to close the learning loop.
"""

import uuid
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.gemini_service import gemini_service
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class ContentAgent:
    """
    Generates marketing copy for regulated insurance brands.
    Enforces brand voice, platform constraints, official JA Assure knowledge grounding,
    and negative constraints from past reviewer feedback.
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._prompt_cache: Dict[str, Dict[str, Any]] = {}

    def load_brand_prompt(self, brand: str) -> Dict[str, Any]:
        """Load brand voice and platform formatting guidelines from YAML."""
        normalized_brand = "jade" if "jade" in brand.lower() else "doctorshield"
        if normalized_brand in self._prompt_cache:
            return self._prompt_cache[normalized_brand]

        yaml_path = self.prompts_dir / f"{normalized_brand}.yaml"
        if not yaml_path.exists():
            logger.warning(f"Brand prompt file not found at {yaml_path}")
            return {"brand_name": brand, "brand_voice": {}}

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._prompt_cache[normalized_brand] = data
            return data

    def generate(
        self,
        topic: str,
        brand: str = "Jade",
        platform: str = "LinkedIn",
        content_type: str = "post",
        research_context: Optional[Dict[str, Any]] = None,
        past_corrections: Optional[List[Dict[str, Any]]] = None,
        force_trigger_flaw: bool = False,
        cycle: int = 1,
    ) -> Dict[str, Any]:
        """
        Generate marketing copy grounded in official JA Assure knowledge.
        Injects past feedback to ensure the model avoids previously rejected claims.
        """
        brand_config = self.load_brand_prompt(brand)
        voice = brand_config.get("brand_voice", {})
        platform_guides = brand_config.get("platform_templates", {}).get(platform, {})

        # Ground in official JA Assure knowledge via Research Agent
        if research_context is None:
            research_context = research_agent.research(brand=brand, topic=topic)
        sources = research_context.get("sources", [])

        # Fetch recent feedback if not provided
        if past_corrections is None:
            past_corrections = feedback_agent.get_recent_feedback(brand=brand, n=5)

        feedback_prompt_section = feedback_agent.format_feedback_for_prompt(past_corrections)

        # Detect if any feedback notes specifically mention payout or guaranteed claims
        has_payout_correction = any(
            "payout" in (c.get("note") or "").lower() or "guarantee" in (c.get("note") or "").lower()
            for c in past_corrections
        )
        has_salesy_correction = any(
            "salesy" in (c.get("tag") or "").lower() or "tone" in (c.get("note") or "").lower()
            for c in past_corrections
        )

        variant_id = f"var-{uuid.uuid4().hex[:6]}"
        fixed_issue: Optional[str] = None

        if past_corrections:
            fixed_issue = f"Applied {len(past_corrections)} past reviewer correction(s): " + "; ".join(
                [f"[{c.get('tag')}]: {c.get('note')}" for c in past_corrections[:2]]
            )

        # Attempt Live Gemini Generation
        generated_content = None
        if gemini_service.is_live and not force_trigger_flaw:
            system_instruction = self._build_system_instruction(brand, voice, platform, platform_guides)
            user_prompt = self._build_user_prompt(
                topic=topic,
                platform=platform,
                content_type=content_type,
                feedback_prompt_section=feedback_prompt_section,
                research_context=research_context,
            )
            generated_content = gemini_service.generate_text(
                prompt=user_prompt,
                system_instruction=system_instruction,
                temperature=0.6,
            )

        # Fallback / Deterministic Generator (ensures 100% demo reliability offline or with API keys)
        if not generated_content:
            generated_content = self._deterministic_generate(
                brand=brand,
                platform=platform,
                content_type=content_type,
                topic=topic,
                force_trigger_flaw=force_trigger_flaw,
                has_payout_correction=has_payout_correction,
                has_salesy_correction=has_salesy_correction,
                cycle=cycle,
            )

        return {
            "content": generated_content,
            "format": platform,
            "brand": brand,
            "platform": platform,
            "content_type": content_type,
            "variant_id": variant_id,
            "fixed_issue": fixed_issue,
            "sources": sources,
            "research_summary": research_context.get("summary", ""),
            "recommendation": research_context.get("recommendation", ""),
        }

    def _build_system_instruction(
        self,
        brand: str,
        voice: Dict[str, Any],
        platform: str,
        platform_guides: Dict[str, Any],
    ) -> str:
        """Construct system prompt enforcing brand persona, regulatory constraints, and anti-hallucination rules."""
        tone = voice.get("tone", "Professional and trustworthy")
        persona = voice.get("persona", "InsurTech advisor")
        vocab_prefer = ", ".join(voice.get("vocabulary_preferences", []))
        vocab_prohibit = ", ".join(voice.get("vocabulary_prohibitions", []))
        format_guide = platform_guides.get("format_guide", "Concise marketing post")
        hashtag_style = platform_guides.get("hashtag_style", "#Insurance")

        return (
            f"You are the senior marketing copywriter for {brand} (a regulated JA Assure InsurTech brand).\n"
            f"BRAND PERSONA: {persona}\n"
            f"TONE: {tone}\n"
            f"PREFERRED VOCABULARY: {vocab_prefer}\n"
            f"PROHIBITED VOCABULARY: {vocab_prohibit}\n"
            f"PLATFORM: {platform}\n"
            f"PLATFORM FORMAT REQUIREMENTS: {format_guide}\n"
            f"RECOMMENDED HASHTAGS: {hashtag_style}\n\n"
            "ANTI-HALLUCINATION & OFFICIAL COMPANY KNOWLEDGE MANDATE:\n"
            "Use only the provided company knowledge for specific JA Assure product facts. If the knowledge context does not support a claim, do not invent the claim.\n"
            "Specifically, NEVER invent:\n"
            "- Coverage limits or dollar amounts not in the knowledge base\n"
            "- Premium percentages or discounts\n"
            "- Claim settlement guarantees or turnaround promises\n"
            "- Unverified product benefits or features\n"
            "- Regulatory approvals, endorsements, or statutory licenses\n"
            "- Market rankings (e.g. '#1 insurer')\n"
            "unless explicitly supported by the provided official JA Assure knowledge.\n\n"
            "SEPARATION OF CONCERNS:\n"
            "- COMPANY KNOWLEDGE: Official factual information regarding JA Assure products and underwriting principles.\n"
            "- REGULATORY COMPLIANCE RULES: Strict regulatory boundaries that evaluate marketing language.\n\n"
            "REGULATORY COMPLIANCE MANDATE (MAS & SE Asian Insurance Standards):\n"
            "1. NEVER promise guaranteed payouts, unconditional settlements, or instant cash.\n"
            "2. NEVER make absolute protection claims like '100% protected', 'zero risk', or 'total immunity'.\n"
            "3. ALWAYS qualify coverage statements with 'subject to policy terms and conditions' or 'underwriting criteria'.\n"
            "4. NEVER use aggressive fearmongering, urgency tactics, or pressure sales gimmicks.\n"
            "5. Output ONLY the finalized marketing copy without meta-commentary."
        )

    def _build_user_prompt(
        self,
        topic: str,
        platform: str,
        content_type: str,
        feedback_prompt_section: str,
        research_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Assemble user prompt including official JA Assure knowledge and recent reviewer feedback."""
        knowledge_section = ""
        if research_context:
            sources_list = research_context.get("sources", [])
            sources_text = "\n".join(
                [f"- {s.get('title')} ({s.get('url')}): {s.get('snippet', '')}" for s in sources_list]
            )
            knowledge_section = (
                "OFFICIAL JA ASSURE COMPANY KNOWLEDGE CONTEXT:\n"
                f"Summary: {research_context.get('summary', '')}\n"
                f"Recommendation: {research_context.get('recommendation', '')}\n"
                f"Sources:\n{sources_text}\n\n"
            )

        return (
            f"Generate a {platform} {content_type} on the following marketing topic:\n"
            f"TOPIC: {topic}\n\n"
            f"{knowledge_section}"
            f"{feedback_prompt_section}\n\n"
            "Write the complete marketing post now adhering strictly to official JA Assure company knowledge:"
        )

    def _deterministic_generate(
        self,
        brand: str,
        platform: str,
        content_type: str,
        topic: str,
        force_trigger_flaw: bool,
        has_payout_correction: bool,
        has_salesy_correction: bool,
        cycle: int,
    ) -> str:
        """
        High-fidelity deterministic copy generator.
        Grounded in official JA Assure resources (Jewellers Block and Medical Indemnity).
        Guarantees clear brand differentiation (Jade ≠ DoctorShield)
        and demonstrates visibly that the system learns from past corrections.
        """
        is_jade = "jade" in brand.lower()

        # CASE A: Flaw triggered (either forced for demo, or cycle 1 without corrections)
        if force_trigger_flaw or (cycle == 1 and not has_payout_correction and not has_salesy_correction):
            if is_jade:
                if platform == "LinkedIn":
                    return (
                        "When safeguarding high-value inventory and fine jewellery collections, standard commercial insurance falls short.\n\n"
                        "At Jade, we provide Jewellers Block coverage with guaranteed payouts on all vault and transit claims for jewelry businesses. "
                        "Our underwriting guarantees your high-value inventory is 100% protected with zero claim disputes and instant cash settlement guaranteed.\n\n"
                        "Act now before your inventory is at risk. Connect with our private client team today.\n\n"
                        "#JewelleryBusiness #JewellersBlock #HighValueInventory #JadeAssure #BespokeProtection"
                    )
                elif platform == "Instagram":
                    return (
                        "Priceless jewelry inventory deserves more than ordinary insurance. ✨💎\n\n"
                        "Jade delivers Jewellers Block protection with guaranteed payouts on all vault and transit losses. "
                        "100% protected, zero risk. Never worry about inventory loss or claim disputes again!\n\n"
                        "👉 Tap the link in bio to secure your jewelry business legacy today.\n\n"
                        "#JewelleryBusiness #JewellersBlock #HighValueInventory #LuxuryAssets #JadeAssure"
                    )
                else:  # X / Twitter
                    return (
                        "Jewellery businesses: standard coverage falls short. Jade Jewellers Block offers guaranteed payouts on all inventory with 100% protection. Secure your stock: https://www.ja-assure.com/blog-jewellers-block.html\n\n#JewellersBlock #InsurTech"
                    )
            else:  # DoctorShield
                if platform == "LinkedIn":
                    return (
                        "Clinical practice in Southeast Asia faces unprecedented legal scrutiny and aggressive malpractice litigation.\n\n"
                        "DoctorShield provides medical practitioners with guaranteed dismissal of patient malpractice claims and 100% immune protection from statutory council inquiries.\n\n"
                        "Patients will sue you tomorrow if you don't act fast. Protect your clinical career immediately.\n\n"
                        "#MedicalIndemnity #HealthcareGovernance #DoctorShield #ClinicalRisk"
                    )
                elif platform == "Instagram":
                    return (
                        "Protecting healthcare heroes across the region. 🩺🛡️\n\n"
                        "DoctorShield guarantees zero risk of medical litigation and complete immunity from patient claims. Guaranteed payout on all legal defense expenses.\n\n"
                        "👉 Schedule your clinical practice consultation via link in bio.\n\n"
                        "#DoctorsOfSEAsia #MedicalPractice #DoctorShield"
                    )
                else:  # X
                    return (
                        "Doctors: Patients will sue you tomorrow without indemnity. DoctorShield offers guaranteed dismissal and 100% protection from malpractice claims.\n\n#MedTwitter #MedicalIndemnity"
                    )

        # CASE B: Compliant Generation (Feedback incorporated / Regenerated output)
        if is_jade:
            if platform == "LinkedIn":
                return (
                    "Protecting high-value jewellery inventory across retail premises, transit routes, and bank vaults requires disciplined risk management, not speculative promises.\n\n"
                    "Grounded in JA Assure's Jewellers Block and Specie Insurance framework, Jade provides bespoke commercial all-risks coverage tailored for jewellery manufacturers, wholesalers, private client collections, and luxury retailers.\n\n"
                    "Core Coverage & Risk Controls:\n"
                    "• Premises & Vault Security: Comprehensive protection against physical loss or damage to inventory, loose diamonds, and precious metals (conditioned on certified safe standards and alarm monitoring).\n"
                    "• Secure Transit & Exhibitions: Tailored transit risk management for professional couriers, with standard exclusions for unattended vehicles.\n"
                    "• Tailored Underwriting: Risk-engineered surveys and customized policy schedules aligned with commercial stock turnover.\n\n"
                    "All coverage terms, limits, and claim settlements are strictly subject to policy terms and conditions, underwriting warranties, and surveyor inspection.\n\n"
                    "Explore official Jewellers Block risk principles: https://www.ja-assure.com/blog-jewellers-block.html\n\n"
                    "#JewelleryBusiness #JewellersBlock #HighValueInventory #RiskManagement #JadeAssure #InsurTech"
                )
            elif platform == "Instagram":
                return (
                    "High-value jewellery inventory requires precision risk management. ✨🛡️\n\n"
                    "Grounded in JA Assure's Jewellers Block framework, Jade delivers tailored commercial protection for jewellers, wholesalers, and luxury retailers.\n\n"
                    "💎 Premises & bank vault coverage\n"
                    "💎 Monitored transit & exhibition protocols\n"
                    "💎 Certified safe & dual-custody standards\n\n"
                    "Coverage is strictly subject to policy terms and conditions and underwriting criteria.\n\n"
                    "👉 Learn more about commercial Jewellers Block at ja-assure.com via link in bio.\n\n"
                    "#JewelleryBusiness #JewellersBlock #HighValueInventory #JadeAssure"
                )
            else:  # X
                return (
                    "Commercial jewellery businesses face unique transit and vault exposures. Grounded in JA Assure's Jewellers Block framework, Jade provides structured risk coverage subject to policy terms & conditions: https://www.ja-assure.com/blog-jewellers-block.html\n\n#JewellersBlock #InsurTech"
                )
        else:  # DoctorShield
            if platform == "LinkedIn":
                return (
                    "Navigating modern healthcare governance requires specialized medico-legal defense counsel and structured clinical risk management.\n\n"
                    "Grounded in JA Assure's Medical Indemnity framework, DoctorShield provides professional indemnity coverage designed for medical specialists, surgeons, and general practitioners across Singapore and Malaysia.\n\n"
                    "Key Medico-Legal Safeguards:\n"
                    "• Dual Function: Specialized legal defense funding for practitioner protection alongside fair patient safety compensation.\n"
                    "• Claims-Made Structure: Protection against claims first made and notified during the policy period, with essential retroactive date coverage for past procedures.\n"
                    "• Statutory Inquiries: Expert legal representation for disciplinary proceedings before medical councils (e.g., SMC, MMC).\n\n"
                    "All indemnity limits, defense cost provisions, and claim settlements are subject to policy terms, conditions, and underwriting schedule.\n\n"
                    "Review official medical indemnity standards: https://www.ja-assure.com/blog-medical-malpractice.html\n\n"
                    "#MedicalIndemnity #HealthcareGovernance #DoctorShield #ClinicalRisk #JAAssure"
                )
            elif platform == "Instagram":
                return (
                    "Dedicated care requires dependable professional defense. 🩺🛡️\n\n"
                    "Grounded in JA Assure's Medical Indemnity principles, DoctorShield delivers specialized indemnity and medico-legal counsel for physicians, surgeons, and clinics.\n\n"
                    "📋 Dual-function defense & patient compensation\n"
                    "📋 Disciplinary inquiry representation (SMC/MMC)\n"
                    "📋 Claims-made structure with retroactive dates\n\n"
                    "Indemnity benefits are strictly subject to policy terms and conditions.\n\n"
                    "👉 Consult our medical defense advisors at ja-assure.com via link in bio.\n\n"
                    "#DoctorsOfSEAsia #MedicalPractice #HealthcareRisk #DoctorShield"
                )
            else:  # X
                return (
                    "Clinical governance begins with professional indemnity. Grounded in JA Assure's Medical Indemnity framework, DoctorShield offers tailored medico-legal defense subject to policy terms & conditions: https://www.ja-assure.com/blog-medical-malpractice.html\n\n#MedTwitter #MedicalIndemnity"
                )


# Global agent instance
content_agent = ContentAgent()
