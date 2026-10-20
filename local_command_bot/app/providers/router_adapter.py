"""Router / Gateway Adapter: Supports OpenRouter, LiteLLM, OneAPI, Groq, and OpenAI-compatible gateways."""

import json
import logging
from typing import Optional, Type
import httpx

from app.providers.base import (
    BaseProviderAdapter, ProviderError, AuthenticationError,
    RateLimitError, TimeoutError, T
)
from app.core.models import TokenUsage

logger = logging.getLogger(__name__)

GATEWAY_PRESETS = {
    "groq": {
        "name": "Groq (LPU Inference)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_var": "GROQ_API_KEY",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        "default_model": "llama-3.3-70b-versatile"
    },
    "openrouter": {
        "name": "OpenRouter (Multi-Cloud Aggregator)",
        "base_url": "https://openrouter.ai/api/v1",
        "env_var": "OPENROUTER_API_KEY",
        "models": [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.1-70b-instruct"
        ],
        "default_model": "anthropic/claude-3.5-sonnet"
    },
    "deepseek": {
        "name": "DeepSeek Official API",
        "base_url": "https://api.deepseek.com/v1",
        "env_var": "DEEPSEEK_API_KEY",
        "models": [
            "deepseek-chat",
            "deepseek-reasoner"
        ],
        "default_model": "deepseek-chat"
    },
    "ollama": {
        "name": "Ollama (Local Offline Inference)",
        "base_url": "http://localhost:11434/v1",
        "env_var": "OLLAMA_API_KEY",
        "models": [
            "llama3.1",
            "qwen2.5:14b",
            "mistral",
            "deepseek-r1:8b"
        ],
        "default_model": "llama3.1"
    },
    "huggingface": {
        "name": "Hugging Face (Serverless Inference)",
        "base_url": "https://api-inference.huggingface.co/v1",
        "env_var": "HUGGINGFACE_API_KEY",
        "models": [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mixtral-8x7B-Instruct-v0.1"
        ],
        "default_model": "mistralai/Mistral-7B-Instruct-v0.3"
    },
    "omniroute": {
        "name": "OmniRoute AI Gateway",
        "base_url": "http://localhost:20128/v1",
        "env_var": "OMNIROUTE_API_KEY",
        "models": [
            "auto",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "groq/llama-3.3-70b-versatile",
            "deepseek/deepseek-chat",
            "mistral/mistral-large-latest",
            "google/gemini-1.5-pro"
        ],
        "default_model": "auto"
    }
}


class RouterAdapter(BaseProviderAdapter):
    """Adapter for unified intermediate AI routers (Groq, OpenRouter, DeepSeek, LiteLLM, Ollama, custom gateways)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "llama-3.3-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1",
        site_name: str = "Local Command Bot",
    ):
        super().__init__(api_key=api_key, default_model=default_model)
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/chat/completions"
        self.site_name = site_name

    def validate_config(self) -> bool:
        # Local servers (Ollama, local proxy) don't strictly require an API key
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return True
        if not self.api_key:
            return False
        return len(self.api_key.strip()) >= 8

    def list_models(self) -> list[str]:
        # Return preset models if matched, or generic popular models
        for preset in GATEWAY_PRESETS.values():
            if preset["base_url"].rstrip("/") == self.base_url:
                return preset["models"]
        return POPULAR_ROUTER_MODELS

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Only attach OpenRouter-specific headers when targeting openrouter.ai
        if "openrouter" in self.base_url.lower():
            headers["HTTP-Referer"] = "https://github.com/local-command-bot"
            headers["X-Title"] = self.site_name
        return headers

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 90.0,
    ) -> tuple[str, TokenUsage]:
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise AuthenticationError(f"Router API Key is missing. Configure it in Settings ({self.base_url}).")

        target_model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(self.api_url, headers=self._build_headers(), json=payload)
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
            f"Provide ONLY the JSON object. Do not wrap with backticks or markdown."
        )

        target_model = model or self.default_model
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(self.api_url, headers=self._build_headers(), json=payload)
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
            raise AuthenticationError("API Key chưa được điền hoặc không đủ ký tự.")

        # 1. Try GET /models first (official standard for Groq, OpenRouter, OpenAI, DeepSeek)
        models_url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(models_url, headers=self._build_headers())
                if res.status_code == 200:
                    return True
                if res.status_code in (401, 403, 429):
                    res.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403, 429):
                raise self.normalize_error(e)
        except Exception:
            pass

        # 2. Fallback to POST /chat/completions ping
        try:
            _, _ = await self.generate("ping", max_tokens=2, timeout=10.0)
            return True
        except Exception as e:
            raise self.normalize_error(e)

    def normalize_error(self, exc: Exception) -> ProviderError:
        """Provide specific diagnostic advice for local Ollama and OmniRoute connection issues."""
        if isinstance(exc, httpx.ConnectError):
            if "11434" in self.base_url or "ollama" in self.base_url.lower():
                return ProviderError(
                    f"Không thể kết nối đến máy chủ Ollama tại {self.base_url}. "
                    f"Vui lòng đảm bảo Ollama đã được cài đặt và đang chạy (gõ lệnh 'ollama serve' trong Terminal).",
                    is_transient=True
                )
            if "20128" in self.base_url or "omniroute" in self.base_url.lower():
                return ProviderError(
                    f"Không thể kết nối đến OmniRoute AI Gateway tại {self.base_url}. "
                    f"Vui lòng khởi động tiến trình OmniRoute Gateway trước khi tiếp tục.",
                    is_transient=True
                )
            return ProviderError(
                f"Lỗi kết nối tới AI Gateway ({self.base_url}): Không thể thiết lập kết nối mạng tới máy chủ.",
                is_transient=True
            )
        return super().normalize_error(exc)

