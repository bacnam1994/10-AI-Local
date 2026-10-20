"""Reviewer Engine: Quality control and critique generation."""

import logging
from typing import Optional
from pathlib import Path

from app.core.models import Task, ReviewResult, TokenUsage
from app.providers import get_adapter
from app.config.settings import PROMPTS_DIR

logger = logging.getLogger(__name__)


class ReviewerEngine:
    """Evaluates drafted sections against quality criteria and returns actionable feedback."""

    def __init__(self, prompt_file: Optional[Path] = None):
        self.prompt_file = prompt_file or (PROMPTS_DIR / "reviewer.md")
        self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        if self.prompt_file.exists():
            return self.prompt_file.read_text(encoding="utf-8")
        return "You are an expert QA Reviewer. Return a structured ReviewResult JSON."

    async def review_section(
        self,
        task: Task,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        dry_run: bool = False,
    ) -> tuple[ReviewResult, TokenUsage]:
        """Critique drafted content and determine whether it passes acceptance criteria."""
        title = task.input.get("title", "Mục Tài Liệu")
        instructions = task.input.get("instructions", "")
        criteria = task.input.get("acceptance_criteria", [])

        prompt = (
            f"VĂN BẢN CẦN THẨM ĐỊNH:\n"
            f"Tiêu đề mục: {title}\n"
            f"Chỉ dẫn ban đầu: {instructions}\n"
            f"Tiêu chí nghiệm thu: {', '.join(criteria)}\n\n"
            f"NỘI DUNG ĐƯỢC SOẠN:\n"
            f"{content}\n\n"
            f"Hãy chấm điểm và xuất ReviewResult JSON."
        )

        effective_provider = provider or task.provider
        effective_model = model or task.model
        provider_name = "mock" if dry_run else effective_provider
        adapter = get_adapter(provider_name, model=effective_model)

        review_res, usage = await adapter.generate_structured(
            prompt=prompt,
            schema_cls=ReviewResult,
            system_prompt=self._system_prompt,
            model=effective_model,
            temperature=0.1
        )

        return review_res, usage
