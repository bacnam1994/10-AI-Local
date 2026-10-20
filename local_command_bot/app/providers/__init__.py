"""Provider package and Adapter Factory."""

from typing import Optional
from app.providers.base import (
    BaseProviderAdapter, ProviderError, AuthenticationError,
    RateLimitError, QuotaExceededError, TimeoutError
)
from app.providers.openai_adapter import OpenAIAdapter
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.gemini_adapter import GeminiAdapter
from app.providers.mock_adapter import MockAdapter
from app.providers.router_adapter import RouterAdapter
from app.security.keyring_manager import secret_manager


def get_adapter(
    provider_name: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BaseProviderAdapter:
    """Factory to instantiate the appropriate adapter for a given provider."""
    p_clean = provider_name.strip().lower()

    # If key wasn't provided directly, look up securely
    resolved_key = api_key or secret_manager.get_api_key(p_clean)

    if p_clean in ("openai", "gpt"):
        return OpenAIAdapter(api_key=resolved_key, default_model=model or "gpt-4o-mini")
    elif p_clean in ("anthropic", "claude"):
        return AnthropicAdapter(api_key=resolved_key, default_model=model or "claude-3-5-sonnet-20241022")
    elif p_clean in ("gemini", "google"):
        return GeminiAdapter(api_key=resolved_key, default_model=model or "gemini-1.5-flash")
    elif p_clean == "groq":
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("groq"),
            default_model=model or "llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1"
        )
    elif p_clean == "deepseek":
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("deepseek"),
            default_model=model or "deepseek-chat",
            base_url="https://api.deepseek.com/v1"
        )
    elif p_clean == "ollama":
        ollama_url = base_url or secret_manager.get_api_key("ollama_url") or "http://localhost:11434/v1"
        return RouterAdapter(
            api_key=resolved_key or "ollama",
            default_model=model or "llama3.1",
            base_url=ollama_url
        )
    elif p_clean in ("omniroute", "omni"):
        omni_url = base_url or secret_manager.get_api_key("omniroute_url") or "http://localhost:20128/v1"
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("omniroute") or "omniroute-local",
            default_model=model or "auto",
            base_url=omni_url
        )
    elif p_clean in ("openrouter", "router"):
        router_url = base_url or secret_manager.get_api_key("openrouter_url") or "https://openrouter.ai/api/v1"
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("openrouter"),
            default_model=model or "anthropic/claude-3.5-sonnet",
            base_url=router_url
        )
    elif p_clean in ("custom", "gateway", "litellm", "oneapi"):
        gateway_url = base_url or secret_manager.get_api_key("custom_gateway_url") or "http://localhost:8000/v1"
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("custom_gateway_key") or "custom-key",
            default_model=model or "custom-model",
            base_url=gateway_url
        )
    elif p_clean in ("huggingface", "hf"):
        return RouterAdapter(
            api_key=resolved_key or secret_manager.get_api_key("huggingface"),
            default_model=model or "mistralai/Mistral-7B-Instruct-v0.3",
            base_url="https://api-inference.huggingface.co/v1"
        )
    elif p_clean in ("mock", "test", "dry_run"):
        return MockAdapter(api_key=resolved_key or "mock-key", default_model=model or "mock-model")
    else:
        raise ValueError(
            f"Unsupported AI provider: '{provider_name}'. Supported: openai, anthropic, gemini, groq, huggingface, openrouter, deepseek, ollama, custom, mock"
        )


__all__ = [
    "BaseProviderAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GeminiAdapter",
    "MockAdapter",
    "RouterAdapter",
    "get_adapter",
    "ProviderError",
    "AuthenticationError",
    "RateLimitError",
    "QuotaExceededError",
    "TimeoutError",
]
