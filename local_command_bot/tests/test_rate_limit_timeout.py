"""Test 10: Rate limit (429) and HTTP timeout error normalization."""

import pytest
import httpx
from app.providers.base import BaseProviderAdapter, RateLimitError, TimeoutError
from app.providers.mock_adapter import MockAdapter


def test_http_error_normalization():
    class DummyAdapter(BaseProviderAdapter):
        def validate_config(self): return True
        def list_models(self): return []
        async def generate(self, *args, **kwargs): pass
        async def generate_structured(self, *args, **kwargs): pass
        async def health_check(self): return True

    adapter = DummyAdapter()

    # 1. Test 429 Rate Limit with Retry-After header
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp_429 = httpx.Response(429, headers={"retry-after": "12.5"}, text="Rate limit exceeded", request=req)
    err_429 = httpx.HTTPStatusError("Rate limited", request=req, response=resp_429)

    norm_err = adapter.normalize_error(err_429)
    assert isinstance(norm_err, RateLimitError)
    assert norm_err.status_code == 429
    assert norm_err.retry_after == 12.5

    # 2. Test Timeout exception
    timeout_exc = httpx.ReadTimeout("Read timed out", request=req)
    norm_timeout = adapter.normalize_error(timeout_exc)
    assert isinstance(norm_timeout, TimeoutError)
    assert norm_timeout.is_transient is True


@pytest.mark.asyncio
async def test_mock_simulates_rate_limit():
    adapter = MockAdapter(simulate_error="ratelimit", fail_attempts_count=1)
    with pytest.raises(RateLimitError) as exc_info:
        await adapter.generate("Test prompt")
    assert exc_info.value.status_code == 429
