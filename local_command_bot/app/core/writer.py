"""Writer Engine: Crafts high-quality document sections adhering to blueprint."""

import logging
from typing import Optional
from pathlib import Path

from app.core.models import Task, TokenUsage
from app.providers import get_adapter
from app.config.settings import PROMPTS_DIR

logger = logging.getLogger(__name__)


class WriterEngine:
    """Orchestrates section drafting by specialized AI models."""

    def __init__(self, prompt_file: Optional[Path] = None):
        self.prompt_file = prompt_file or (PROMPTS_DIR / "writer.md")
        self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        if self.prompt_file.exists():
            return self.prompt_file.read_text(encoding="utf-8")
        return "You are an expert Technical Writer for pharmaceutical SOPs and specifications."

    async def draft_section(
        self,
        task: Task,
        previous_context: str = "",
        critiques_to_fix: Optional[list[str]] = None,
        dry_run: bool = False,
    ) -> tuple[str, TokenUsage]:
        """Draft or revise a document section."""
        inp = task.input
        title = inp.get("title", "Mục Tài Liệu")
        instructions = inp.get("instructions", "")
        criteria = inp.get("acceptance_criteria", [])
        references = inp.get("references", [])
        doc_objective = inp.get("document_objective", "")

        prompt_parts = [
            f"MỤC TIÊU TÀI LIỆU CHÍNH: {doc_objective}",
            f"PHÂN ĐOẠN ĐANG SOẠN THẢO: {title}",
            f"CHỈ DẪN KỸ THUẬT: {instructions}",
            f"TIÊU CHÍ NGHIỆM THU: {', '.join(criteria) if criteria else 'Đầy đủ, chuẩn mực'}",
            f"CĂN CỨ THAM CHIẾU: {', '.join(references) if references else 'Quy chuẩn hiện hành'}"
        ]

        if previous_context:
            prompt_parts.append(f"\nBỐI CẢNH CÁC PHẦN ĐÃ SOẠN TRƯỚC ĐÓ:\n{previous_context[-2000:]}")

        if critiques_to_fix:
            critique_list = "\n- ".join(critiques_to_fix)
            prompt_parts.append(
                f"\nYÊU CẦU SỬA ĐỔI TỪ REVIEWER (VÒNG TRƯỚC CHƯA ĐẠT):\n- {critique_list}\n"
                f"Hãy khắc phục triệt để các điểm yếu trên trong bản soạn thảo mới."
            )

        prompt_text = "\n\n".join(prompt_parts)

        # Force mock adapter if dry run
        provider_name = "mock" if dry_run else task.provider
        adapter = get_adapter(provider_name, model=task.model)

        content, usage = await adapter.generate(
            prompt=prompt_text,
            system_prompt=self._system_prompt,
            model=task.model,
            temperature=0.4,
            max_tokens=4096
        )

        return content, usage
