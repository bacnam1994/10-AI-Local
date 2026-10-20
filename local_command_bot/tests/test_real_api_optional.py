"""Test Live Service Connectivity and Streamlined Pipeline (Optional Integration Tests).

These tests verify real connections to Ollama and OmniRoute Gateway.
They automatically skip gracefully if services are not running or credentials are not configured,
ensuring offline unit test suites remain fast and reliable.
"""

import httpx
import pytest
from pathlib import Path
from docx import Document

from app.providers import get_adapter
from app.providers.base import ProviderError, TimeoutError as AppTimeoutError
from app.core.models import Job, OutputFormat, JobStatus
from app.core.orchestrator import Orchestrator
from app.security.keyring_manager import secret_manager
from app.config.settings import settings


async def is_service_reachable(url: str, timeout: float = 2.0) -> bool:
    """Helper to check if a local AI service endpoint is currently alive."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        return False


@pytest.mark.asyncio
async def test_live_ollama_connectivity_optional():
    """Verify live connectivity and generation with local Ollama service."""
    ollama_url = settings.ollama_base_url.rstrip("/")
    if not await is_service_reachable(f"{ollama_url}/tags"):
        pytest.skip(
            f"Bỏ qua test live Ollama: Dịch vụ chưa phản hồi tại {ollama_url}. "
            f"Chạy 'ollama serve' trong Terminal để kích hoạt test tích hợp thật."
        )

    adapter = get_adapter("ollama", base_url=ollama_url)
    is_healthy = await adapter.health_check()
    assert is_healthy is True

    # Test short real generation
    try:
        content, usage = await adapter.generate(
            prompt="Trả lời ngắn gọn bằng 1 từ: Bạn có sẵn sàng không?",
            max_tokens=10,
            timeout=5.0
        )
        assert len(content.strip()) > 0
        assert usage.total_tokens > 0
    except (AppTimeoutError, TimeoutError, ProviderError) as e:
        pytest.skip(f"Ollama đang chạy nhưng nạp model chậm ({e}).")


@pytest.mark.asyncio
async def test_live_omniroute_connectivity_optional():
    """Verify live connectivity and generation with OmniRoute Gateway."""
    omni_url = settings.omniroute_base_url.rstrip("/")
    if not await is_service_reachable(f"{omni_url}/models"):
        pytest.skip(
            f"Bỏ qua test live OmniRoute: Gateway chưa phản hồi tại {omni_url}. "
            f"Khởi động OmniRoute Gateway để kích hoạt test tích hợp thật."
        )

    adapter = get_adapter("omniroute", base_url=omni_url)
    is_healthy = await adapter.health_check()
    assert is_healthy is True

    try:
        content, usage = await adapter.generate(
            prompt="Trả lời bằng 1 từ: OK",
            max_tokens=10,
            timeout=5.0
        )
        assert len(content.strip()) > 0
        assert usage.total_tokens > 0
    except (AppTimeoutError, TimeoutError, ProviderError) as e:
        pytest.skip(f"OmniRoute đang chạy nhưng upstream cloud tạm thời chưa phản hồi ({e}).")



@pytest.mark.asyncio
async def test_live_streamlined_pipeline_e2e_optional(temp_db, temp_output_dir):
    """End-to-End Test: Live Ollama (Planning) -> Live OmniRoute (Writing) -> DOCX synthesis."""
    ollama_url = settings.ollama_base_url.rstrip("/")
    omni_url = settings.omniroute_base_url.rstrip("/")

    ollama_up = await is_service_reachable(f"{ollama_url}/tags")
    omni_up = await is_service_reachable(f"{omni_url}/models")

    if not (ollama_up and omni_up):
        pytest.skip(
            f"Bỏ qua test E2E thực tế: Cần cả Ollama ({'Online' if ollama_up else 'Offline'}) "
            f"và OmniRoute ({'Online' if omni_up else 'Offline'}) đang chạy."
        )

    orch = Orchestrator(state_store=temp_db)
    job = Job(
        job_id="live_e2e_test_001",
        prompt="Soạn thảo quy trình khử trùng thiết bị phòng sạch cấp D theo Thông tư 35/2018/TT-BYT.",
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.DOCX],
        dry_run=False  # Real live execution
    )
    temp_db.save_job(job)

    finished_job = await orch.run_job(
        job=job,
        planner_provider="ollama",
        planner_model="llama3.1",
        writer_provider="omniroute",
        writer_model="auto"
    )

    assert finished_job.status == JobStatus.SUCCEEDED
    assert len(finished_job.generated_files) >= 1
    docx_file = Path(finished_job.generated_files[0])
    assert docx_file.exists()
    assert docx_file.stat().st_size > 1000

    doc = Document(str(docx_file))
    full_text = "\n".join([p.text for p in doc.paragraphs])
    assert "DRAFT" in full_text


@pytest.mark.asyncio
async def test_legacy_live_openai_optional():
    """Legacy check for OpenAI API key if present."""
    live_key = secret_manager.get_api_key("openai")
    if not live_key or live_key.startswith("mock") or len(live_key) < 20:
        pytest.skip("Bỏ qua test live API do chưa cấu hình OPENAI_API_KEY thực tế.")

    adapter = get_adapter("openai", api_key=live_key)
    is_healthy = await adapter.health_check()
    assert is_healthy is True
