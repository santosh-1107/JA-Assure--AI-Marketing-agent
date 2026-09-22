"""
Content Agent for JA Assure AI Marketing Agent.
Generates platform- and brand-tailored marketing assets grounded in official JA Assure knowledge.
Orchestrates generation via Gemini (Live AI Mode) or dynamic offline engine.
Incorporates human feedback as few-shot constraints and tracks full generation metadata.
"""

import uuid
import yaml
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.services.llm_service import llm_service, LLMGenerationError
from backend.agents.feedback_agent import feedback_agent
from backend.agents.research_agent import research_agent
from backend.services.groq_guardrails import (
    build_groq_system_prompt,
    build_groq_user_prompt,
    validate_brand_knowledge_match,
    claim_grounding_verifier,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
VALID_BRANDS = {"Jade", "DoctorShield"}
VALID_PLATFORMS = {"LinkedIn", "Instagram", "X"}
VALID_CONTENT_TYPES = {"post", "carousel", "tweet", "video_script"}


class ContentAgent:
    """
    Generates marketing copy for regulated insurance brands.
    Enforces brand voice, platform constraints, official JA Assure PDF knowledge grounding,
    negative constraints from past reviewer feedback, and generation metadata tracking.
    Uses LLMService (Groq primary, Gemini fallback).
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._prompt_cache: Dict[str, Dict[str, Any]] = {}
        self.llm_service = llm_service

    def load_brand_prompt(self, brand: str) -> Dict[str, Any]:
        """
        Load brand voice and platform guidelines from YAML.
        Strictly validates brand name without silent fallbacks.
        """
        if brand not in VALID_BRANDS:
            raise ValueError(f"Invalid brand '{brand}'. Must be one of: {sorted(VALID_BRANDS)}")

        normalized_brand = brand.lower()
        if normalized_brand in self._prompt_cache:
            return self._prompt_cache[normalized_brand]

        yaml_path = self.prompts_dir / f"{normalized_brand}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Brand prompt file not found at {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._prompt_cache[normalized_brand] = data
            return data

    def generate_content(
        self,
        topic: str,
        brand: str = "Jade",
        platform: str = "LinkedIn",
        content_type: str = "post",
        rag_context: Optional[Any] = None,
        competitor_context: Optional[Any] = None,
        past_feedback: Optional[Any] = None,
        additional_instruction: Optional[str] = None,
        product: Optional[str] = None,
        force_trigger_flaw: bool = False,
        cycle: int = 1,
        allow_offline_fallback: bool = False,
        num_variants: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate marketing copy grounded in official JA Assure knowledge.
        Strictly enforces mandatory topic, brand isolation, and RAG grounding.
        Routes through LLMService (Groq primary, Gemini fallback).
        """
        # Strict topic validation
        if topic is None or not str(topic).strip():
            raise ValueError("Topic is mandatory and cannot be empty.")
        clean_topic = str(topic).strip()

        # Strict parameter validation
        if brand not in VALID_BRANDS:
            raise ValueError(f"Invalid brand '{brand}'. Must be one of: {sorted(VALID_BRANDS)}")
        if platform not in VALID_PLATFORMS:
            raise ValueError(f"Invalid platform '{platform}'. Must be one of: {sorted(VALID_PLATFORMS)}")
        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be one of: {sorted(VALID_CONTENT_TYPES)}")

        resolved_product = product or ("Jewellers Block & Specie" if brand == "Jade" else "Medical Malpractice Indemnity")

        brand_config = self.load_brand_prompt(brand)
        voice = brand_config.get("brand_voice", {})
        platform_guides = brand_config.get("platform_templates", {}).get(platform, {})
        prompt_version = str(brand_config.get("prompt_version", "1.0"))

        # 1. Ground in official JA Assure knowledge via Research Agent (Tier 1 & Tier 3)
        research_context = rag_context or kwargs.get("research_context")
        if research_context is None:
            research_context = research_agent.research(brand=brand, topic=clean_topic, product=resolved_product)
        elif isinstance(research_context, list):
            research_context = {"sources": research_context}

        # Attach competitor context if explicitly provided
        if competitor_context:
            if isinstance(competitor_context, dict):
                research_context["competitor_analysis"] = competitor_context
            elif isinstance(competitor_context, list):
                research_context["competitor_analysis"] = {"competitors": competitor_context}

        sources = research_context.get("sources", [])
        knowledge_ids = [s.get("id") for s in sources if s.get("id")]

        # Retain detailed source citations
        retrieved_sources = []
        for s in sources:
            retrieved_sources.append({
                "filename": s.get("filename", f"{s.get('id', 'ja_assure')}.pdf"),
                "page_number": int(s.get("page_number", 1)),
                "section": s.get("section", "General"),
                "relevance_score": float(s.get("relevance_score", 1.0)),
                "source_type": s.get("source_type", "official_pdf"),
                "product": s.get("product", resolved_product),
                "brand": s.get("brand", brand),
            })

        # 2. Retrieve semantic feedback if not explicitly provided (Tier 2 Reviewer Corrections)
        past_corrections = past_feedback if past_feedback is not None else kwargs.get("past_corrections")
        if past_corrections is None:
            past_corrections = feedback_agent.retrieve_semantic_feedback(
                topic=clean_topic,
                brand=brand,
                product=resolved_product,
                platform=platform,
                top_k=4,
            )

        feedback_ids = [c.get("feedback_id") or c.get("id") for c in past_corrections if (c.get("feedback_id") or c.get("id"))]
        feedback_prompt_section = feedback_agent.format_feedback_for_prompt(past_corrections)

        variant_id = f"var-{uuid.uuid4().hex[:6]}"
        fixed_issue: Optional[str] = None

        if past_corrections:
            fixed_issue = f"Applied {len(past_corrections)} reviewer correction(s): " + "; ".join(
                [f"[{c.get('tag') or c.get('rejection_tag')}]: {c.get('note') or c.get('reviewer_note')}" for c in past_corrections[:2]]
            )

        # 3. Brand Guardrail Knowledge Matching Check
        is_match, mismatch_reason = validate_brand_knowledge_match(
            requested_brand=brand,
            requested_product=resolved_product,
            authoritative_sources=sources,
        )
        if not is_match or not sources:
            logger.warning(f"Brand/product knowledge mismatch: {mismatch_reason or 'No authoritative sources'}")
            insufficient_msg = "Insufficient authoritative knowledge for this product request."
            return {
                "content": insufficient_msg,
                "brand": brand,
                "product": resolved_product,
                "platform": platform,
                "content_type": content_type,
                "topic": clean_topic,
                "variant_id": variant_id,
                "provider": "guardrail",
                "generation_mode": "guardrail",
                "model": "groq-guardrail",
                "prompt_version": prompt_version,
                "knowledge_source_ids": knowledge_ids,
                "feedback_ids": feedback_ids,
                "retrieved_sources": retrieved_sources,
                "feedback_context_ids": feedback_ids,
                "generation_metadata": {
                    "is_live_llm": False,
                    "model_used": "groq-guardrail",
                    "provider": "guardrail",
                    "guardrail_status": "INSUFFICIENT_KNOWLEDGE",
                    "reason": mismatch_reason or "No authoritative sources found for requested topic.",
                },
                "fixed_issue": fixed_issue,
                "sources": sources,
                "research_summary": research_context.get("summary", ""),
                "recommendation": research_context.get("recommendation", ""),
                "claims_used": [],
                "uncertain_claims": [],
                "feedback_applied": [],
                "claim_grounding": [],
                "generation_status": "INSUFFICIENT_KNOWLEDGE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # 4. Handle intentional flaw simulation (for compliance testing/demo gates)
        if force_trigger_flaw:
            flawed_copy = self._dynamic_offline_generate(
                brand=brand,
                brand_config=brand_config,
                platform=platform,
                content_type=content_type,
                topic=clean_topic,
                research_context=research_context,
                past_corrections=past_corrections,
                additional_instruction=additional_instruction,
                force_trigger_flaw=True,
            )
            # Evaluate grounding on flawed copy
            extracted_flaw_claims = claim_grounding_verifier.extract_claims(flawed_copy)
            flaw_grounding = claim_grounding_verifier.verify_grounding(extracted_flaw_claims, sources, brand)
            return {
                "content": flawed_copy,
                "brand": brand,
                "product": resolved_product,
                "platform": platform,
                "content_type": content_type,
                "topic": clean_topic,
                "variant_id": variant_id,
                "provider": "simulation",
                "generation_mode": "simulation",
                "model": "flaw-generator",
                "prompt_version": prompt_version,
                "knowledge_source_ids": knowledge_ids,
                "feedback_ids": feedback_ids,
                "retrieved_sources": retrieved_sources,
                "feedback_context_ids": feedback_ids,
                "generation_metadata": {
                    "is_live_llm": False,
                    "model_used": "flaw-generator",
                    "flaw_forced": True,
                    "provider": "simulation",
                },
                "fixed_issue": None,
                "sources": sources,
                "research_summary": research_context.get("summary", ""),
                "recommendation": research_context.get("recommendation", ""),
                "claims_used": [],
                "uncertain_claims": [],
                "feedback_applied": [],
                "claim_grounding": flaw_grounding,
                "generation_status": "SUCCESS",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # 5. Live LLM Generation via LLMService (Groq primary -> Gemini fallback)
        system_instruction = self._build_system_instruction(brand, voice, platform, platform_guides, product=resolved_product)
        user_prompt = self._build_user_prompt(
            topic=clean_topic,
            brand=brand,
            product=resolved_product,
            platform=platform,
            content_type=content_type,
            feedback_prompt_section=feedback_prompt_section,
            research_context=research_context,
            additional_instruction=additional_instruction,
        )

        claims_used = []
        uncertain_claims = []
        feedback_applied = []
        generation_status = "SUCCESS"

        try:
            llm_result = self.llm_service.generate_content(
                prompt=user_prompt,
                system_instruction=system_instruction,
                temperature=0.5,
                enforce_structured=True,
            )
            generated_content = llm_result["content"]
            provider_used = llm_result["provider"]
            model_used = llm_result["model"]
            generation_mode = provider_used
            claims_used = llm_result.get("claims_used", [])
            uncertain_claims = llm_result.get("uncertain_claims", [])
            feedback_applied = llm_result.get("feedback_applied", [])
            generation_status = llm_result.get("generation_status", "SUCCESS")

        except LLMGenerationError as e:
            if not allow_offline_fallback:
                raise

            logger.warning(f"Live LLM generation failed across providers: {e}. Executing verified dynamic offline generator.")
            generated_content = self._dynamic_offline_generate(
                brand=brand,
                brand_config=brand_config,
                platform=platform,
                content_type=content_type,
                topic=clean_topic,
                research_context=research_context,
                past_corrections=past_corrections,
                additional_instruction=additional_instruction,
                force_trigger_flaw=False,
            )
            provider_used = "offline"
            model_used = "offline-engine"
            generation_mode = "offline"

        # Handle multiple variant diversity if requested
        variants = []
        if num_variants > 1:
            variant_angles = [
                ("Operational Risk & Custody Focus", "Emphasize day-to-day operational vulnerabilities and physical risk management."),
                ("Financial & Legal Governance Focus", "Emphasize litigation financing, balance-sheet defense, and statutory compliance."),
                ("Executive Thought-Leadership Focus", "Emphasize market leadership, comparative industry risk, and strategic continuity."),
            ]
            for v_idx in range(num_variants):
                v_angle_title, v_angle_desc = variant_angles[v_idx % len(variant_angles)]
                v_inst = f"Angle {v_idx + 1} ({v_angle_title}): {v_angle_desc} " + (additional_instruction or "")
                v_prompt = self._build_user_prompt(
                    topic=clean_topic,
                    brand=brand,
                    product=resolved_product,
                    platform=platform,
                    content_type=content_type,
                    feedback_prompt_section=feedback_prompt_section,
                    research_context=research_context,
                    additional_instruction=v_inst,
                )
                try:
                    v_llm = self.llm_service.generate_content(
                        prompt=v_prompt,
                        system_instruction=system_instruction,
                        temperature=0.6 + (v_idx * 0.1),
                        enforce_structured=True,
                    )
                    v_content = v_llm["content"]
                except Exception:
                    v_content = self._dynamic_offline_generate(
                        brand=brand,
                        brand_config=brand_config,
                        platform=platform,
                        content_type=content_type,
                        topic=clean_topic,
                        research_context=research_context,
                        past_corrections=past_corrections,
                        additional_instruction=v_inst,
                        force_trigger_flaw=False,
                        variant_index=v_idx,
                    )
                variants.append({
                    "variant_id": f"var-{uuid.uuid4().hex[:6]}",
                    "angle": v_angle_title,
                    "content": v_content,
                    "platform": platform,
                    "content_type": content_type,
                    "topic": clean_topic,
                })

        # 6. Post-generation Claim Extraction & Grounding Layer
        extracted_claims = claim_grounding_verifier.extract_claims(
            content=generated_content,
            claims_from_llm=claims_used,
        )
        claim_grounding = claim_grounding_verifier.verify_grounding(
            claims=extracted_claims,
            authoritative_sources=sources,
            brand=brand,
        )

        timestamp_str = datetime.now(timezone.utc).isoformat()

        return {
            "content": generated_content,
            "brand": brand,
            "product": resolved_product,
            "platform": platform,
            "content_type": content_type,
            "topic": clean_topic,
            "variant_id": variant_id,
            "provider": provider_used,
            "generation_mode": generation_mode,
            "model": model_used,
            "prompt_version": prompt_version,
            "knowledge_source_ids": knowledge_ids,
            "feedback_ids": feedback_ids,
            "retrieved_sources": retrieved_sources,
            "feedback_context_ids": feedback_ids,
            "generation_metadata": {
                "is_live_llm": (provider_used in ("groq", "gemini")),
                "model_used": model_used,
                "provider": provider_used,
                "knowledge_count": len(sources),
                "feedback_count": len(past_corrections),
                "flaw_forced": False,
                "additional_instruction_used": bool(additional_instruction),
            },
            "fixed_issue": fixed_issue,
            "sources": sources,
            "research_summary": research_context.get("summary", ""),
            "recommendation": research_context.get("recommendation", ""),
            "claims_used": claims_used,
            "uncertain_claims": uncertain_claims,
            "feedback_applied": feedback_applied,
            "claim_grounding": claim_grounding,
            "generation_status": generation_status,
            "variants": variants if variants else [],
            "timestamp": timestamp_str,
        }

    def generate(
        self,
        topic: str,
        brand: str = "Jade",
        product: Optional[str] = None,
        platform: str = "LinkedIn",
        content_type: str = "post",
        research_context: Optional[Dict[str, Any]] = None,
        past_corrections: Optional[List[Dict[str, Any]]] = None,
        additional_instruction: Optional[str] = None,
        force_trigger_flaw: bool = False,
        cycle: int = 1,
        allow_offline_fallback: bool = True,
        num_variants: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Backward-compatible wrapper routing to generate_content.
        """
        return self.generate_content(
            topic=topic,
            brand=brand,
            platform=platform,
            content_type=content_type,
            rag_context=research_context,
            past_feedback=past_corrections,
            additional_instruction=additional_instruction,
            product=product,
            force_trigger_flaw=force_trigger_flaw,
            cycle=cycle,
            allow_offline_fallback=allow_offline_fallback,
            num_variants=num_variants,
            **kwargs,
        )

    def _build_system_instruction(
        self,
        brand: str,
        voice: Dict[str, Any],
        platform: str,
        platform_guides: Dict[str, Any],
        product: Optional[str] = None,
    ) -> str:
        """Construct system prompt enforcing brand persona, regulatory constraints, and anti-hallucination rules."""
        return build_groq_system_prompt(
            brand=brand,
            platform=platform,
            product=product,
            voice=voice,
            platform_guides=platform_guides,
        )

    def _build_user_prompt(
        self,
        topic: str,
        platform_or_brand: str = "LinkedIn",
        content_type_or_product: str = "post",
        feedback_prompt_section: str = "",
        *args,
        brand: Optional[str] = None,
        product: Optional[str] = None,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        research_context: Optional[Dict[str, Any]] = None,
        additional_instruction: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Assemble user prompt strictly separating the 4 knowledge and regulatory tiers."""
        # Resolve arguments for backward-compatibility with positional test calls
        if brand is None:
            brand = "Jade" if platform_or_brand in ("LinkedIn", "Instagram", "X") else platform_or_brand
        if platform is None:
            platform = platform_or_brand if platform_or_brand in ("LinkedIn", "Instagram", "X") else "LinkedIn"
        if content_type is None:
            content_type = content_type_or_product if content_type_or_product in ("post", "carousel", "video_script") else "post"
        if product is None:
            product = content_type_or_product if content_type_or_product not in ("post", "carousel", "video_script") else ("Jewellers Block & Specie" if brand == "Jade" else "Medical Malpractice Indemnity")

        authoritative_sources = research_context.get("sources", []) if research_context else []
        competitor_analysis = research_context.get("competitor_analysis") if research_context else None

        return build_groq_user_prompt(
            topic=topic,
            brand=brand,
            product=product,
            platform=platform,
            content_type=content_type,
            authoritative_sources=authoritative_sources,
            compliance_rules=None,
            historical_feedback=feedback_prompt_section,
            competitor_intelligence=competitor_analysis,
            user_directive=additional_instruction,
        )
    def _dynamic_offline_generate(
        self,
        brand: str,
        brand_config: Dict[str, Any],
        platform: str,
        content_type: str,
        topic: str,
        research_context: Dict[str, Any],
        past_corrections: List[Dict[str, Any]],
        additional_instruction: Optional[str] = None,
        force_trigger_flaw: bool = False,
        variant_index: int = 0,
    ) -> str:
        """
        Data-driven dynamic offline generator.
        Assembles marketing copy dynamically from brand YAML guidelines, retrieved JA Assure knowledge facts,
        and platform constraints with angle, hook, and CTA diversity.
        """
        voice = brand_config.get("brand_voice", {})
        platform_guides = brand_config.get("platform_templates", {}).get(platform, {})
        mandatory_qualifier = brand_config.get(
            "mandatory_qualifier",
            "All coverage terms, limits, and claim assessments are subject to policy terms, conditions, and underwriting schedule."
        )
        base_cta = platform_guides.get("cta", "Contact JA Assure private client advisory.")
        hashtags = platform_guides.get("hashtag_style", "#Insurance")

        # Extract verified facts from knowledge research
        sources = research_context.get("sources", [])
        extracted_facts = []
        for s in sources:
            for fact in s.get("key_facts", []):
                if fact not in extracted_facts:
                    extracted_facts.append(fact)

        facts_text = ""
        if extracted_facts:
            facts_text = "\n".join([f"• {f}" for f in extracted_facts[:3]])
        elif research_context.get("summary"):
            facts_text = f"• {research_context.get('summary')}"

        # CASE 1: Intentional Flaw Simulation (for demonstrating compliance gate detection)
        if force_trigger_flaw:
            flaw_cfg = brand_config.get("flaw_simulation", {})
            prohibited_claim = flaw_cfg.get(
                "prohibited_phrase",
                "guaranteed payouts on all losses with 100% protection"
            )
            urgency = flaw_cfg.get("urgency_phrase", "Act now before your business is at risk!")

            if platform == "X":
                return (
                    f"{brand}: When managing risk, standard coverage falls short. "
                    f"Our underwriting offers {prohibited_claim}. {urgency}\n\n{hashtags}"
                )
            elif platform == "Instagram":
                return (
                    f"Protecting what matters most. ✨🛡️\n\n"
                    f"Regarding '{topic}': {brand} delivers {prohibited_claim}.\n\n"
                    f"{urgency}\n\n"
                    f"{base_cta}\n\n{hashtags}"
                )
            else:  # LinkedIn
                return (
                    f"When addressing '{topic}', standard commercial property insurance falls short.\n\n"
                    f"At {brand}, we provide underwriting with {prohibited_claim}.\n\n"
                    f"{urgency}\n\n"
                    f"{base_cta}\n\n{hashtags}"
                )

        # CASE 2: Compliant Dynamic Assembly with Hook & Angle Diversity
        pref_vocab = voice.get("vocabulary_preferences", ["bespoke protection", "risk management"])
        lead_phrase = pref_vocab[0].capitalize() if pref_vocab else "Specialized protection"

        # Diverse hooks and angles based on variant index and topic
        hooks = [
            f"Managing exposures around '{topic}' demands verified underwriting protocols rather than speculative market assumptions.",
            f"When evaluating '{topic}', high-exposure operations require specialized risk engineering that generic policies overlook.",
            f"Strategic risk engineering for '{topic}': how disciplined underwriting safeguards balance sheets and operational continuity.",
        ]
        selected_hook = hooks[variant_index % len(hooks)]

        ctas = [
            f"Consult the {brand} advisory desk to review tailored underwriting schedules.",
            f"Request a confidential risk assessment with JA Assure specialist advisors.",
            f"Connect with our private underwriting team to evaluate customized coverage terms.",
        ]
        selected_cta = ctas[variant_index % len(ctas)]

        add_note = ""
        if additional_instruction and additional_instruction.strip():
            add_note = f"\nFocus: {additional_instruction.strip()}\n"

        if platform == "X":
            return (
                f"{lead_phrase} for {topic}. Grounded in disciplined underwriting principles: "
                f"{mandatory_qualifier} {selected_cta} {hashtags}"
            )[:278]

        elif platform == "Instagram":
            emoji_header = "💎🛡️" if brand == "Jade" else "🩺🛡️"
            return (
                f"{lead_phrase}: {topic} {emoji_header}\n\n"
                f"{selected_hook}\n\n"
                f"Underwriting highlights:\n"
                f"{facts_text}\n"
                f"{add_note}\n"
                f"{mandatory_qualifier}\n\n"
                f"{selected_cta}\n\n"
                f"{hashtags}"
            )

        else:  # LinkedIn & Post
            return (
                f"{selected_hook}\n\n"
                f"At {brand}, our advisory framework is grounded in verified underwriting criteria:\n\n"
                f"{facts_text}\n"
                f"{add_note}\n"
                f"{mandatory_qualifier}\n\n"
                f"{selected_cta}\n\n"
                f"{hashtags}"
            )


# Global content agent instance
content_agent = ContentAgent()
