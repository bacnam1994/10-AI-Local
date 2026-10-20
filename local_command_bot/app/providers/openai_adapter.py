"""OpenAI Provider Adapter implementation."""

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

OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo"
]


class OpenAIAdapter(BaseProviderAdapter):
    """Adapter for official OpenAI REST API."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gpt-4o-mini"):
        super().__init__(api_key=api_key, default_model=default_model)
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def validate_config(self) -> bool:
        if not self.api_key or not self.api_key.startswith("sk-"):
            return False
        return len(self.api_key.strip()) > 20

    def list_models(self) -> list[str]:
        return OPENAI_MODELS

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
            raise AuthenticationError("OpenAI API Key is missing. Configure it in Settings.")

        target_model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(self.api_url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                content = data["choices"][0]["message"]["content"]
                usage_raw = data.get("usage", {})
                p_tokens = usage_raw.get("prompt_tokens", 0)
                c_tokens = usage_raw.get("completion_tokens", 0)
                t_tokens = usage_raw.get("total_tokens", p_tokens + c_tokens)
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
            f"Do not include markdown code block backticks around the json if possible, or provide valid raw json."
        )

        target_model = model or self.default_model
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt}
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(self.api_url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                raw_text = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(raw_text)
                structured_obj = schema_cls.model_validate(parsed_json)

                usage_raw = data.get("usage", {})
                p_tokens = usage_raw.get("prompt_tokens", 0)
                c_tokens = usage_raw.get("completion_tokens", 0)
                cost = self.calculate_cost(target_model, p_tokens, c_tokens)

                return structured_obj, TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=cost
                )
        except Exception as e:
            raise self.normalize_error(e)

    async def health_check(self) -> bool:
        if not self.validate_config():
            return False
        try:
            _, _ = await self.generate("ping", max_tokens=2, timeout=10.0)
            return True
        except Exception as e:
            logger.debug(f"OpenAI health check failed: {e}")
            return False
