"""
LLM Service Abstraction for JA Assure AI Marketing Intelligence Agent.
Provides unified generation interface with Groq as primary provider and Gemini fallback.
Enforces strict anti-hallucination and rejects silent fallback to hardcoded marketing copy.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from project root
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    """Raised when live LLM generation fails across configured providers."""
    pass


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.5,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass


class GroqProvider(BaseLLMProvider):
    """
    Primary LLM provider using Groq API.
    Provides ultra-low latency inference using models such as llama-3.3-70b-versatile.
    Supports strict structured JSON generation.
    """

    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self._client = None
        if self.api_key:
            try:
                import groq
                self._client = groq.Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

    def is_available(self) -> bool:
        key = os.getenv("GROQ_API_KEY", self.api_key).strip()
        return bool(key and len(key) > 5)

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "groq",
            "model": os.getenv("GROQ_MODEL", self.model),
            "configured": self.is_available(),
        }

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.5,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        key = os.getenv("GROQ_API_KEY", self.api_key).strip()
        if not key or len(key) <= 5:
            raise LLMGenerationError("Groq API key not configured or invalid.")

        if not self._client or self.api_key != key:
            import groq
            self.api_key = key
            self._client = groq.Groq(api_key=self.api_key)

        model_name = os.getenv("GROQ_MODEL", self.model)
        candidate_models = [model_name]
        for fallback_m in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]:
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_err = None
        for m in candidate_models:
            create_kwargs: Dict[str, Any] = {
                "model": m,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 3500,
            }
            if response_format:
                create_kwargs["response_format"] = response_format

            try:
                chat_completion = self._client.chat.completions.create(**create_kwargs)
                choice = chat_completion.choices[0]
                content = choice.message.content or ""
                self.model = m
                return content.strip()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # If error is specifically about response_format parameter, retry without it
                if "response_format" in err_str and response_format:
                    logger.info(f"Groq model '{m}' rejected response_format, retrying with prompt instructions...")
                    create_kwargs.pop("response_format", None)
                    try:
                        chat_completion = self._client.chat.completions.create(**create_kwargs)
                        choice = chat_completion.choices[0]
                        content = choice.message.content or ""
                        self.model = m
                        return content.strip()
                    except Exception as retry_err:
                        last_err = retry_err
                        err_str = str(retry_err).lower()

                if any(x in err_str for x in ["model_not_found", "does not exist", "rate limit", "tokens per day", "tpd", "429"]):
                    logger.info(f"Groq model '{m}' unavailable ({err_str[:60]}), trying next candidate...")
                    continue
                else:
                    raise LLMGenerationError(f"Groq API error: {e}") from e

        logger.error(f"Groq generation failed across all candidate models: {last_err}")
        raise LLMGenerationError(f"Groq API error: {last_err}") from last_err


class GeminiProvider(BaseLLMProvider):
    """
    Secondary fallback LLM provider using Google Gemini API.
    """

    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "gemini",
            "model": self.model,
            "configured": self.is_available(),
        }

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.5,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        if not self.is_available():
            raise LLMGenerationError("Gemini API key not configured or invalid.")

        try:
            from backend.gemini_service import gemini_service
            # Re-read key in case set dynamically
            gemini_service.api_key = self.api_key
            gemini_service.is_live = True
            text = gemini_service.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
            )
            if not text or len(text.strip()) < 10:
                raise LLMGenerationError("Gemini returned empty or invalid text.")
            return text.strip()
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise LLMGenerationError(f"Gemini API error: {e}") from e


class MockTestProvider(BaseLLMProvider):
    """
    Test mock provider used during automated test executions or offline harness.
    Generates compliant test marketing copy without calling external cloud APIs.
    Supports structured JSON format when requested.
    """

    def __init__(self, provider_name: str = "test_mock", model: str = "test-mock-engine", should_fail: bool = False):
        self.provider_name = provider_name
        self.model = model
        self.should_fail = should_fail

    def is_available(self) -> bool:
        return True

    def get_info(self) -> Dict[str, Any]:
        return {"provider": self.provider_name, "model": self.model, "configured": True}

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.5,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        if self.should_fail:
            raise LLMGenerationError(f"Mock failure from {self.provider_name}")
        brand = "Jade" if "Jade" in prompt or "jade" in prompt.lower() else "DoctorShield"
        product = "Jewellers Block & Specie" if brand == "Jade" else "Medical Malpractice Indemnity"
        platform = "LinkedIn" if "LinkedIn" in prompt else ("Instagram" if "Instagram" in prompt else "X")

        # Extract topic dynamically from prompt
        topic_match = "Specialist risk engineering"
        for line in prompt.splitlines():
            line_s = line.strip()
            if line_s.startswith("CURRENT USER REQUEST:"):
                topic_match = line_s.split(":", 1)[1].strip()
                break
            elif line_s.startswith("Topic:"):
                topic_match = line_s.split(":", 1)[1].strip()
                break

        mock_body = (
            f"Addressing '{topic_match}' for {brand} ({product}) on {platform}. "
            "Our advisory framework delivers specialized risk engineering and tailored underwriting criteria. "
            "All coverage terms, limits, and claim assessments are subject to policy terms, "
            "conditions, and underwriter schedule. Contact JA Assure private client advisory."
        )

        # If structured JSON is expected
        if response_format or "OUTPUT SCHEMA" in system_instruction or "claims_used" in prompt or "claims_used" in system_instruction:
            import json
            return json.dumps({
                "content": mock_body,
                "brand": brand,
                "product": product,
                "platform": platform,
                "topic": topic_match,
                "claims_used": [
                    {"claim": f"Specialized risk engineering for {topic_match}", "source_id": f"ja_{brand.lower()}_guide", "page": 1}
                ],
                "uncertain_claims": [],
                "feedback_applied": [],
                "generation_status": "SUCCESS",
            })

        return mock_body


class LLMService:
    """
    Orchestrates LLM providers.
    Directs generation to Groq by default; gracefully falls back to Gemini.
    Enforces strict guardrail validation with 1-retry repair on structured JSON.
    Raises LLMGenerationError if providers fail.
    """

    def __init__(
        self,
        primary_provider: Optional[BaseLLMProvider] = None,
        fallback_provider: Optional[BaseLLMProvider] = None,
    ):
        self.groq_provider = primary_provider or GroqProvider()
        self.gemini_provider = fallback_provider or GeminiProvider()
        self.mock_provider: Optional[BaseLLMProvider] = None

    def set_mock_provider(self, provider: Optional[BaseLLMProvider]):
        """Inject mock provider for automated offline testing."""
        self.mock_provider = provider

    def get_active_provider_name(self) -> str:
        """Identify which provider will be attempted first."""
        if self.mock_provider and self.mock_provider.is_available():
            return "test_mock"
        preferred = os.getenv("LLM_PROVIDER", "groq").lower()
        if preferred == "gemini" and self.gemini_provider.is_available():
            return "gemini"
        if self.groq_provider.is_available():
            return "groq"
        if self.gemini_provider.is_available():
            return "gemini"
        return "none"

    def check_health(self) -> Dict[str, Any]:
        """Return health and readiness status for all configured providers."""
        return {
            "active_preference": os.getenv("LLM_PROVIDER", "groq"),
            "groq": self.groq_provider.get_info(),
            "gemini": self.gemini_provider.get_info(),
            "has_live_provider": (self.groq_provider.is_available() or self.gemini_provider.is_available()),
        }

    def generate_content(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.5,
        enforce_structured: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute generation following the primary -> fallback hierarchy.
        If enforce_structured is True (or prompt specifies OUTPUT SCHEMA),
        strictly forces JSON output and performs a 1-retry repair on malformed output.
        Flow:
          ContentAgent -> LLMService -> GroqProvider
          If Groq fails -> GeminiProvider fallback
          If both fail -> raise LLMGenerationError
        """
        from backend.services.groq_guardrails import (
            validate_and_parse_groq_output,
            repair_groq_output,
            GroqOutputValidationError,
        )

        should_structure = enforce_structured or ("OUTPUT SCHEMA" in system_instruction) or ("claims_used" in prompt)
        response_fmt = {"type": "json_object"} if should_structure else None

        # 1. Check test mock provider
        if self.mock_provider and self.mock_provider.is_available():
            text = self.mock_provider.generate(prompt, system_instruction, temperature, response_format=response_fmt)
            if should_structure:
                try:
                    parsed = validate_and_parse_groq_output(text)
                    return {
                        "content": parsed["content"],
                        "brand": parsed.get("brand"),
                        "product": parsed.get("product"),
                        "platform": parsed.get("platform"),
                        "topic": parsed.get("topic"),
                        "claims_used": parsed.get("claims_used", []),
                        "uncertain_claims": parsed.get("uncertain_claims", []),
                        "feedback_applied": parsed.get("feedback_applied", []),
                        "generation_status": parsed.get("generation_status", "SUCCESS"),
                        "provider": "test_mock",
                        "model": "test-mock-engine",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                except GroqOutputValidationError:
                    pass
            return {
                "content": text,
                "provider": "test_mock",
                "model": "test-mock-engine",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        preferred = os.getenv("LLM_PROVIDER", "groq").lower()
        primary = self.groq_provider if preferred == "groq" else self.gemini_provider
        secondary = self.gemini_provider if preferred == "groq" else self.groq_provider

        # Extract metadata for required debug logging (without logging keys/secrets)
        req_topic = "N/A"
        req_brand = "N/A"
        req_platform = "N/A"
        for line in prompt.splitlines():
            ls = line.strip()
            if ls.startswith("CURRENT USER REQUEST:"):
                req_topic = ls.split(":", 1)[1].strip()
            elif ls.startswith("Topic:"):
                req_topic = ls.split(":", 1)[1].strip()
            elif ls.startswith("BRAND:") or ls.startswith("Brand:"):
                req_brand = ls.split(":", 1)[1].strip()
            elif ls.startswith("PLATFORM:") or ls.startswith("Platform:"):
                req_platform = ls.split(":", 1)[1].strip()

        logger.info(
            f"\n==================================================\n"
            f"CONTENT GENERATION REQUEST\n"
            f"Topic: {req_topic}\n"
            f"Brand: {req_brand}\n"
            f"Platform: {req_platform}\n\n"
            f"FINAL LLM PROMPT\n"
            f"{prompt}\n"
            f"=================================================="
        )

        errors = []

        for provider in [primary, secondary]:
            if not provider.is_available():
                errors.append(f"{provider.get_info()['provider']}: API key not configured.")
                continue

            try:
                raw_content = provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    response_format=response_fmt,
                )
                info = provider.get_info()

                if should_structure:
                    try:
                        parsed = validate_and_parse_groq_output(raw_content)
                    except GroqOutputValidationError as val_err:
                        logger.warning(f"Provider {info['provider']} emitted non-schema output: {val_err}. Executing 1-retry repair...")
                        try:
                            parsed = repair_groq_output(
                                repair_callable=lambda p: provider.generate(p, temperature=0.1),
                                malformed_output=raw_content,
                                validation_error=str(val_err),
                            )
                        except GroqOutputValidationError as repair_err:
                            logger.error(f"Structured repair retry failed on {info['provider']}: {repair_err}")
                            raise LLMGenerationError(
                                f"{info['provider']} structured output failed schema validation after repair attempt: {repair_err}"
                            ) from repair_err

                    return {
                        "content": parsed["content"],
                        "brand": parsed.get("brand"),
                        "product": parsed.get("product"),
                        "platform": parsed.get("platform"),
                        "topic": parsed.get("topic"),
                        "claims_used": parsed.get("claims_used", []),
                        "uncertain_claims": parsed.get("uncertain_claims", []),
                        "feedback_applied": parsed.get("feedback_applied", []),
                        "generation_status": parsed.get("generation_status", "SUCCESS"),
                        "provider": info["provider"],
                        "model": info["model"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                return {
                    "content": raw_content,
                    "provider": info["provider"],
                    "model": info["model"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            except Exception as e:
                p_name = provider.get_info()["provider"]
                logger.warning(f"Provider {p_name} error: {e}")
                errors.append(f"{p_name}: {e}")

        # If both providers fail: Return clear generation error. Do not silently generate fake/demo content.
        err_msg = (
            "LLM generation failed across all available providers.\n"
            + "\n".join([f"  - {err}" for err in errors])
            + "\nTo enable live generation, please provide a valid GROQ_API_KEY or GEMINI_API_KEY in .env. "
            "Silent fallback to hardcoded marketing copy is disabled to ensure regulatory compliance."
        )
        raise LLMGenerationError(err_msg)


# Global service instance
llm_service = LLMService()
