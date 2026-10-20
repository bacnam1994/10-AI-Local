"""Test 11: Provider Adapter interface and Mock Adapter verification."""

import pytest
from app.providers import get_adapter
from app.core.models import JobPlan, ReviewResult, TokenUsage


@pytest.mark.asyncio
async def test_mock_adapter_structured_jobplan():
    adapter = get_adapter("mock")
    assert adapter.validate_config()
    assert await adapter.health_check()

    plan, usage = await adapter.generate_structured(
        prompt="Soạn thảo SOP",
        schema_cls=JobPlan
    )
    assert isinstance(plan, JobPlan)
    assert len(plan.tasks) > 0
    assert usage.prompt_tokens > 0


@pytest.mark.asyncio
async def test_mock_adapter_structured_review():
    adapter = get_adapter("mock")
    review, usage = await adapter.generate_structured(
        prompt="Rà soát nội dung",
        schema_cls=ReviewResult
    )
    assert isinstance(review, ReviewResult)
    assert review.is_approved is True
    assert review.score >= 8.0
