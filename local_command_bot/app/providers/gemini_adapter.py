"""Google Gemini Provider Adapter implementation."""

import re
import json
import logging
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel

from app.providers.base import (
    BaseProviderAdapter, ProviderError, AuthenticationError,
    RateLimitError, TimeoutError, T
)
from app.core.models import TokenUsage

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash"
]


class GeminiAdapter(BaseProviderAdapter):
    """Adapter for official Google Gemini REST API."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-1.5-flash"):
        super().__init__(api_key=api_key, default_model=default_model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def validate_config(self) -> bool:
        if not self.api_key:
            return False
        return len(self.api_key.strip()) >= 25

    def list_models(self) -> list[str]:
        return GEMINI_MODELS

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 90.0,
    ) -> tuple[str, TokenUsage]:
        if not self.api_key:
            raise AuthenticationError("Gemini API Key is missing. Configure it in Settings.")

        target_model = model or self.default_model
        url = f"{self.base_url}/{target_model}:generateContent?key={self.api_key}"

        payload: dict = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                # Extract text
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError("Gemini returned empty candidate list.")

                parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join(p.get("text", "") for p in parts)

                usage_meta = data.get("usageMetadata", {})
                p_tokens = usage_meta.get("promptTokenCount", 0)
                c_tokens = usage_meta.get("candidatesTokenCount", 0)
                t_tokens = usage_meta.get("totalTokenCount", p_tokens + c_tokens)
                cost = self.calculate_cost(target_model, p_tokens, c_tokens)

                return content, TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=cost
                )
        except Exception as e:
            raise self.normalize_error(e)

    async def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 90.0,
    ) -> tuple[T, TokenUsage]:
        schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
        instruction = (
            f"{system_prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON Schema:\n{schema_json}\n"
            f"Output ONLY the JSON object. Do not wrap with backticks."
        )

        target_model = model or self.default_model
        url = f"{self.base_url}/{target_model}:generateContent?key={self.api_key}"

        payload: dict = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": instruction}]
            },
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
                res.raise_for_status()
                data = res.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError("Gemini returned empty candidate list.")

                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = "".join(p.get("text", "") for p in parts).strip()

                # Clean up if enclosed in markdown
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)

                parsed = json.loads(raw_text)
                obj = schema_cls.model_validate(parsed)

                usage_meta = data.get("usageMetadata", {})
                p_tokens = usage_meta.get("promptTokenCount", 0)
                c_tokens = usage_meta.get("candidatesTokenCount", 0)
                t_tokens = usage_meta.get("totalTokenCount", p_tokens + c_tokens)
                cost = self.calculate_cost(target_model, p_tokens, c_tokens)

                return obj, TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=cost
                )
        except Exception as e:
            raise self.normalize_error(e)

    async def health_check(self) -> bool:
        if not self.validate_config():
            return False
        try:
            _, _ = await self.generate("ping", max_tokens=5, timeout=10.0)
            return True
        except Exception as e:
            logger.debug(f"Gemini health check failed: {e}")
            return False
