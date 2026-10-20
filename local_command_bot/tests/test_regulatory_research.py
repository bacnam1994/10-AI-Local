"""Test Regulatory Reference Verification Engine (P0 Requirements)."""

import pytest
from app.core.models import Job, utc_now
from app.research.researcher import (
    ResearchEngine,
    STATUS_CATALOG_SUGGESTION,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED_ONLINE,
)


@pytest.mark.asyncio
async def test_research_engine_curated_reference_not_auto_verified(temp_db):
    """Verify that matching a curated GMP regulation does NOT forge verified_at or clause."""
    engine = ResearchEngine(state_store=temp_db)
    job_id = "test_regulatory_001"

    # Save dummy job
    job = Job(job_id=job_id, prompt="Test SOP", output_dir=".")
    temp_db.save_job(job)

    # Research query with known reference
    refs = await engine.research_for_job(job_id, ["Thông tư 35/2018/TT-BYT"])
    assert len(refs) == 1
    ref = refs[0]

    # Verify attributes
    assert ref.doc_number == "35/2018/TT-BYT"
    assert ref.status == STATUS_CATALOG_SUGGESTION
    assert ref.verified_at is None  # MUST NOT auto-set verification timestamp
    assert ref.clause_used is None  # MUST NOT speculate clause without concrete verification

    # Verify persisted in StateStore
    db_refs = temp_db.get_source_references(job_id)
    assert len(db_refs) == 1
    assert db_refs[0].verified_at is None
    assert db_refs[0].clause_used is None


@pytest.mark.asyncio
async def test_research_engine_unverified_reference(temp_db):
    """Verify that uncatalogued references are explicitly flagged as UNVERIFIED."""
    engine = ResearchEngine(state_store=temp_db)
    job_id = "test_regulatory_002"
    temp_db.save_job(Job(job_id=job_id, prompt="Test SOP", output_dir="."))

    refs = await engine.research_for_job(job_id, ["Tiêu chuẩn nội bộ phòng thí nghiệm XYZ"])
    assert len(refs) == 1
    ref = refs[0]

    assert ref.status == STATUS_UNVERIFIED
    assert ref.verified_at is None
    assert ref.clause_used is None
    assert ref.issuing_body == "Chưa xác minh"


@pytest.mark.asyncio
async def test_manual_or_online_verification(temp_db):
    """Verify that legitimate verification updates the status and timestamp correctly."""
    engine = ResearchEngine(state_store=temp_db)
    job_id = "test_regulatory_003"
    temp_db.save_job(Job(job_id=job_id, prompt="Test SOP", output_dir="."))

    refs = await engine.research_for_job(job_id, ["Dược điển Việt Nam V"])
    assert len(refs) == 1
    ref = refs[0]
    assert ref.verified_at is None

    # Perform legitimate verification step
    verified_ref = engine.mark_reference_verified(
        reference=ref,
        verified_status=STATUS_VERIFIED_ONLINE,
        clause_used="Phụ lục 13.8 — Thử vô trùng"
    )

    assert verified_ref.verified_at is not None
    assert verified_ref.status == STATUS_VERIFIED_ONLINE
    assert verified_ref.clause_used == "Phụ lục 13.8 — Thử vô trùng"

    # Check persistence in DB
    reloaded = temp_db.get_source_references(job_id)[0]
    assert reloaded.verified_at is not None
    assert reloaded.status == STATUS_VERIFIED_ONLINE
    assert reloaded.clause_used == "Phụ lục 13.8 — Thử vô trùng"
