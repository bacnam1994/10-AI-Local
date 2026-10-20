"""Test 9: Graceful handling when AI provider API key is missing."""

import pytest
from app.providers.openai_adapter import OpenAIAdapter
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.gemini_adapter import GeminiAdapter
from app.providers.base import AuthenticationError


@pytest.mark.asyncio
async def test_missing_openai_key():
    adapter = OpenAIAdapter(api_key="")
    assert not adapter.validate_config()
    with pytest.raises(AuthenticationError):
        await adapter.generate("Hello")


@pytest.mark.asyncio
async def test_missing_anthropic_key():
    adapter = AnthropicAdapter(api_key=None)
    assert not adapter.validate_config()
    with pytest.raises(AuthenticationError):
        await adapter.generate("Hello")


@pytest.mark.asyncio
async def test_missing_gemini_key():
    adapter = GeminiAdapter(api_key="")
    assert not adapter.validate_config()
    with pytest.raises(AuthenticationError):
        await adapter.generate("Hello")
