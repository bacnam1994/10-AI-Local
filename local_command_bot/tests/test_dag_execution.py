"""Test 3: Dependency execution order and cycle detection in DAG."""

import pytest
from app.core.models import Task, TaskStatus, TaskRole
from app.core.scheduler import DAGScheduler, DependencyCycleError, MissingDependencyError


def test_dag_topological_order(temp_db):
    scheduler = DAGScheduler(temp_db)

    # Setup tasks: t3 depends on t2; t2 depends on t1; t1 has no dependencies
    t1 = Task(task_id="t1", job_id="j1", role=TaskRole.RESEARCHER, provider="mock", model="m", dependencies=[])
    t2 = Task(task_id="t2", job_id="j1", role=TaskRole.WRITER, provider="mock", model="m", dependencies=["t1"])
    t3 = Task(task_id="t3", job_id="j1", role=TaskRole.REVIEWER, provider="mock", model="m", dependencies=["t2"])

    sorted_ids = scheduler.validate_dag([t3, t1, t2])
    assert sorted_ids == ["t1", "t2", "t3"]


def test_dag_cycle_detection(temp_db):
    scheduler = DAGScheduler(temp_db)

    # Cyclic dependency: t1 -> t2 -> t1
    t1 = Task(task_id="t1", job_id="j1", role=TaskRole.WRITER, provider="mock", model="m", dependencies=["t2"])
    t2 = Task(task_id="t2", job_id="j1", role=TaskRole.WRITER, provider="mock", model="m", dependencies=["t1"])

    with pytest.raises(DependencyCycleError):
        scheduler.validate_dag([t1, t2])


def test_dag_missing_dependency(temp_db):
    scheduler = DAGScheduler(temp_db)

    t1 = Task(task_id="t1", job_id="j1", role=TaskRole.WRITER, provider="mock", model="m", dependencies=["non_existent"])
    with pytest.raises(MissingDependencyError):
        scheduler.validate_dag([t1])
