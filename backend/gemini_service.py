"""
Gemini LLM Service for JA Assure AI Marketing Agent.
Handles Google AI Studio API calls with timeout, retry, error handling,
and deterministic fallback generation for offline/local hackathon demos.
"""

import os
import json
import logging
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiService:
    """
    Service wrapper for Google Gemini Flash API.
    Gracefully falls back to high-fidelity deterministic generation if API key is missing or offline.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model
        self.is_live = bool(self.api_key and len(self.api_key) > 8 and not self.api_key.startswith("your_"))

    def check_health(self) -> Dict[str, Any]:
        """Check API configuration and availability status."""
        return {
            "is_live": self.is_live,
            "model": self.model,
            "has_key": bool(self.api_key),
            "mode": "Google AI Studio Live" if self.is_live else "Deterministic InsurTech Engine (Offline/Demo Mode)",
        }

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> Optional[str]:
        """
        Send a generation request to Google AI Studio API.
        Returns the generated text response, or None if the API fails or is unconfigured.
        """
        if not self.is_live:
            return None

        url = f"{BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        contents: List[Dict[str, Any]] = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"[SYSTEM INSTRUCTION]\n{system_instruction}\n[END SYSTEM INSTRUCTION]"}],
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly follow all instructions and brand constraints."}],
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}],
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                else:
                    logger.warning(
                        f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}"
                    )
        except Exception as exc:
            logger.warning(f"Gemini API request failed: {exc}")

        return None


# Global service instance
gemini_service = GeminiService()
