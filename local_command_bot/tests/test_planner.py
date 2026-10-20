"""Test 1: Planner creates valid JobPlan from sample prompt."""

import pytest
from app.core.planner import PlannerEngine
from app.core.models import JobPlan, TaskRole


@pytest.mark.asyncio
async def test_planner_creates_valid_plan():
    planner = PlannerEngine()
    sample_prompt = (
        "Soạn thảo SOP Vệ sinh và Khử trùng Phòng sạch cấp D theo tiêu chuẩn GMP-WHO (Thông tư 35/2018/TT-BYT)"
    )

    plan, usage = await planner.create_plan(
        user_prompt=sample_prompt,
        provider_name="mock",
        budget_limit=5.0,
        time_limit=300.0,
        dry_run=True
    )

    assert isinstance(plan, JobPlan)
    assert plan.objective != ""
    assert len(plan.tasks) >= 3
    assert plan.budget_limit_usd == 5.0
    assert plan.time_limit_seconds == 300.0
    assert usage.total_tokens > 0

    # Verify task roles and non-empty titles
    for t in plan.tasks:
        assert t.task_id != ""
        assert t.title != ""
        assert isinstance(t.role, TaskRole)
