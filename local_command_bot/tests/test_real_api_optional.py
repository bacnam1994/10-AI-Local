"""Test 20: Optional Live Cloud API Integration Test (Skipped when no key provided)."""

import os
import pytest
from app.providers import get_adapter
from app.security.keyring_manager import secret_manager


@pytest.mark.asyncio
async def test_live_api_integration_optional():
    live_key = secret_manager.get_api_key("openai")
    if not live_key or live_key.startswith("mock") or len(live_key) < 20:
        pytest.skip("Bỏ qua test live API do chưa cấu hình OPENAI_API_KEY thực tế.")

    adapter = get_adapter("openai", api_key=live_key)
    is_healthy = await adapter.health_check()
    assert is_healthy is True
