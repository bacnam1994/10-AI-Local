"""Test 2: Schema validation detects malformed plans and missing required fields."""

import pytest
from pydantic import ValidationError
from app.core.models import JobPlan, TaskPlanItem, TaskRole
from app.core.planner import PlannerEngine, PlannerError


def test_invalid_jobplan_schema_fails():
    # Missing required 'objective' and 'tasks'
    with pytest.raises(ValidationError):
        JobPlan.model_validate({})

    # Empty objective rejected by semantic validator
    planner = PlannerEngine()
    invalid_plan = JobPlan(
        objective="",
        tasks=[]
    )
    with pytest.raises(PlannerError) as exc_info:
        planner.validate_plan(invalid_plan)
    assert "Objective is missing" in str(exc_info.value)


def test_duplicate_task_id_rejected():
    planner = PlannerEngine()
    invalid_plan = JobPlan(
        objective="Mục tiêu hợp lệ",
        tasks=[
            TaskPlanItem(task_id="dup_id", title="Task 1", role=TaskRole.WRITER, instructions="A"),
            TaskPlanItem(task_id="dup_id", title="Task 2", role=TaskRole.WRITER, instructions="B")
        ]
    )
    with pytest.raises(PlannerError) as exc_info:
        planner.validate_plan(invalid_plan)
    assert "Duplicate task_id" in str(exc_info.value)


def test_self_dependency_rejected():
    planner = PlannerEngine()
    invalid_plan = JobPlan(
        objective="Mục tiêu hợp lệ",
        tasks=[
            TaskPlanItem(task_id="t1", title="Task 1", role=TaskRole.WRITER, instructions="A", dependencies=["t1"])
        ]
    )
    with pytest.raises(PlannerError) as exc_info:
        planner.validate_plan(invalid_plan)
    assert "cannot depend on itself" in str(exc_info.value)
