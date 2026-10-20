"""Anthropic Claude Provider Adapter implementation."""

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

ANTHROPIC_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229"
]


class AnthropicAdapter(BaseProviderAdapter):
    """Adapter for official Anthropic Messages API."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key=api_key, default_model=default_model)
        self.api_url = "https://api.anthropic.com/v1/messages"

    def validate_config(self) -> bool:
        if not self.api_key or not self.api_key.startswith("sk-ant-"):
            return False
        return len(self.api_key.strip()) > 20

    def list_models(self) -> list[str]:
        return ANTHROPIC_MODELS

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
            raise AuthenticationError("Anthropic API Key is missing. Configure it in Settings.")

        target_model = model or self.default_model
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(self.api_url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                # Extract content
                text_blocks = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
                content = "".join(text_blocks)

                usage_raw = data.get("usage", {})
                p_tokens = usage_raw.get("input_tokens", 0)
                c_tokens = usage_raw.get("output_tokens", 0)
                cost = self.calculate_cost(target_model, p_tokens, c_tokens)

                return content, TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=p_tokens + c_tokens,
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
            f"You MUST output valid, parseable JSON conforming strictly to this JSON Schema:\n{schema_json}\n"
            f"Output ONLY the JSON object. Do not wrap in markdown or add commentary."
        )

        content, usage = await self.generate(
            prompt=prompt,
            system_prompt=instruction,
            model=model,
            temperature=temperature,
            timeout=timeout
        )

        # Extract json substring if wrapped in markdown
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            obj = schema_cls.model_validate(parsed)
            return obj, usage
        except Exception as e:
            raise ProviderError(f"Anthropic returned invalid structured JSON: {e}\nRaw output: {content[:300]}")

    async def health_check(self) -> bool:
        if not self.validate_config():
            return False
        try:
            _, _ = await self.generate("ping", max_tokens=5, timeout=10.0)
            return True
        except Exception as e:
            logger.debug(f"Anthropic health check failed: {e}")
            return False
