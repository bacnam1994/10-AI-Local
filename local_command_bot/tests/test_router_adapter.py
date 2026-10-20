"""Test for RouterAdapter (Groq, OpenRouter, DeepSeek, Ollama, Custom Gateways)."""

import pytest
from app.providers import get_adapter, RouterAdapter
from app.providers.base import AuthenticationError


def test_router_adapter_instantiation_and_config():
    # 1. Validation fails without key on remote gateway
    adapter_empty = RouterAdapter(api_key="", base_url="https://openrouter.ai/api/v1")
    assert not adapter_empty.validate_config()

    # 2. Validation passes with standard router key
    adapter = RouterAdapter(
        api_key="sk-or-v1-abcdef1234567890abcdef",
        default_model="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1"
    )
    assert adapter.validate_config()

    headers = adapter._build_headers()
    assert "Bearer sk-or-v1-" in headers["Authorization"]
    assert "HTTP-Referer" in headers
    assert "X-Title" in headers


def test_get_adapter_groq_factory():
    groq_key = "gsk_1234567890abcdefghijklmnopqrstuvwxyz"
    adapter = get_adapter("groq", api_key=groq_key, model="llama-3.3-70b-versatile")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "https://api.groq.com/openai/v1/chat/completions"
    assert adapter.default_model == "llama-3.3-70b-versatile"
    assert adapter.validate_config()
    assert "llama-3.3-70b-versatile" in adapter.list_models()


def test_get_adapter_deepseek_factory():
    deepseek_key = "sk-deepseek-1234567890abcdef"
    adapter = get_adapter("deepseek", api_key=deepseek_key, model="deepseek-chat")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "https://api.deepseek.com/v1/chat/completions"
    assert adapter.default_model == "deepseek-chat"
    assert adapter.validate_config()


def test_get_adapter_ollama_factory():
    # Ollama on localhost does not require a remote API key
    adapter = get_adapter("ollama", model="llama3.1")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "http://localhost:11434/v1/chat/completions"
    assert adapter.default_model == "llama3.1"
    assert adapter.validate_config()  # Validates True for localhost


def test_get_adapter_openrouter_factory():
    adapter = get_adapter("openrouter", api_key="sk-or-v1-testkey12345678", model="deepseek/deepseek-chat")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.default_model == "deepseek/deepseek-chat"


def test_get_adapter_custom_gateway():
    custom_url = "http://localhost:8000/v1"
    adapter = get_adapter(
        "gateway",
        api_key="custom-secret-key-12345",
        model="meta-llama/llama-3.1-70b",
        base_url=custom_url
    )
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "http://localhost:8000/v1/chat/completions"


def test_get_adapter_huggingface_factory():
    hf_key = "hf_1234567890abcdefghijklmnopqrstuvwx"
    adapter = get_adapter("huggingface", api_key=hf_key, model="mistralai/Mistral-7B-Instruct-v0.3")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "https://api-inference.huggingface.co/v1/chat/completions"
    assert adapter.default_model == "mistralai/Mistral-7B-Instruct-v0.3"
    assert adapter.validate_config()


def test_get_adapter_omniroute_factory():
    # OmniRoute on http://localhost:20128/v1
    adapter = get_adapter("omniroute", model="auto")
    assert isinstance(adapter, RouterAdapter)
    assert adapter.api_url == "http://localhost:20128/v1/chat/completions"
    assert adapter.default_model == "auto"
    assert adapter.validate_config()
    assert "auto" in adapter.list_models()
    assert "anthropic/claude-3.5-sonnet" in adapter.list_models()
