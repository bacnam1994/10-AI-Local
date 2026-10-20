"""Deterministic Mock Provider Adapter for testing, dry-runs, and simulations."""

import asyncio
import logging
from typing import Optional, Type, TypeVar, Any
from pydantic import BaseModel

from app.providers.base import (
    BaseProviderAdapter, ProviderError, AuthenticationError,
    RateLimitError, TimeoutError, T
)
from app.core.models import (
    TokenUsage, JobPlan, TaskPlanItem, TaskRole, ReviewResult, ReviewCritique
)

logger = logging.getLogger(__name__)


class MockAdapter(BaseProviderAdapter):
    """Deterministic Mock Adapter for tests and dry-run execution."""

    def __init__(
        self,
        api_key: Optional[str] = "mock-secret-key-1234567890",
        default_model: str = "mock-model",
        simulate_error: Optional[str] = None,
        fail_attempts_count: int = 0,
        fixed_text: Optional[str] = None,
        review_approved: bool = True,
        delay_seconds: float = 0.05,
    ):
        super().__init__(api_key=api_key, default_model=default_model)
        self.simulate_error = simulate_error
        self.fail_attempts_count = fail_attempts_count
        self.fixed_text = fixed_text
        self.review_approved = review_approved
        self.delay_seconds = delay_seconds
        self._current_attempt = 0

    def validate_config(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def list_models(self) -> list[str]:
        return ["mock-model", "mock-pro-model"]

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 90.0,
    ) -> tuple[str, TokenUsage]:
        self._current_attempt += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        # Error simulation check
        if self.simulate_error:
            if self.fail_attempts_count == 0 or self._current_attempt <= self.fail_attempts_count:
                if self.simulate_error == "network":
                    raise ProviderError("Mock network connection refused (ECONNREFUSED)", is_transient=True)
                elif self.simulate_error == "auth":
                    raise AuthenticationError("Mock invalid API key (401)")
                elif self.simulate_error == "ratelimit":
                    raise RateLimitError("Mock rate limit exceeded (429)", retry_after=0.2)
                elif self.simulate_error == "timeout":
                    raise TimeoutError("Mock connection timeout after 90s")
                elif self.simulate_error == "quota":
                    raise ProviderError("Mock quota exceeded", status_code=429)

        if self.fixed_text:
            text = self.fixed_text
        else:
            text = (
                f"### Nội dung giả lập cho yêu cầu\n\n"
                f"Phần tài liệu mẫu được sinh tự động bởi MockAdapter.\n"
                f"- Mục tiêu: Đảm bảo tuân thủ tiêu chuẩn GMP và SOP liên quan.\n"
                f"- Các bước thực hiện chi tiết đã được đối chiếu quy chuẩn kỹ thuật.\n\n"
                f"Ghi chú: [DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT]\n"
            )

        usage = TokenUsage(
            prompt_tokens=150,
            completion_tokens=250,
            total_tokens=400,
            estimated_cost_usd=0.0005
        )
        return text, usage

    async def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 90.0,
    ) -> tuple[T, TokenUsage]:
        self._current_attempt += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.simulate_error:
            if self.fail_attempts_count == 0 or self._current_attempt <= self.fail_attempts_count:
                if self.simulate_error == "network":
                    raise ProviderError("Mock network error", is_transient=True)
                elif self.simulate_error == "auth":
                    raise AuthenticationError("Mock auth error")
                elif self.simulate_error == "ratelimit":
                    raise RateLimitError("Mock ratelimit", retry_after=0.2)

        # Generate realistic default structured response according to target schema
        if schema_cls is JobPlan or schema_cls.__name__ == "JobPlan":
            plan = JobPlan(
                objective="Quy trình Thao tác Chuẩn (SOP) Vệ sinh và Khử trùng Phòng sạch cấp D",
                doc_type="SOP",
                language="Vietnamese",
                target_audience="Nhân viên sản xuất và Giám sát QA",
                scope="Khu vực phòng sạch cấp D - Phân xưởng sản xuất",
                output_structure=[
                    "1. Mục đích và Phạm vi",
                    "2. Trách nhiệm và Quyền hạn",
                    "3. Thiết bị, Hóa chất và Dụng cụ",
                    "4. Quy trình Vệ sinh và Khử trùng Chi tiết",
                    "5. Giám sát Vi sinh và Đánh giá Chất lượng",
                    "6. Hồ sơ, Biểu mẫu và Lưu trữ"
                ],
                tasks=[
                    TaskPlanItem(
                        task_id="task_research",
                        title="Nghiên cứu văn bản pháp quy Dược điển và GMP-WHO",
                        role=TaskRole.RESEARCHER,
                        provider="mock",
                        model="mock-model",
                        instructions="Rà soát các quy chuẩn vệ sinh phòng sạch Dược phẩm theo Thông tư 35/2018/TT-BYT.",
                        dependencies=[],
                        result_format="markdown",
                        acceptance_criteria=["Liệt kê đủ quy chuẩn liên quan", "Ghi chú tình trạng xác minh"]
                    ),
                    TaskPlanItem(
                        task_id="task_sec_1_2",
                        title="Soạn thảo Mục 1 & 2: Mục đích, Phạm vi và Trách nhiệm",
                        role=TaskRole.WRITER,
                        provider="mock",
                        model="mock-model",
                        instructions="Soạn thảo mục đích, phạm vi áp dụng và ma trận trách nhiệm RACI.",
                        dependencies=["task_research"],
                        result_format="markdown",
                        acceptance_criteria=["Rõ ràng trách nhiệm QA/QC/Sản xuất", "Không dùng placeholder"]
                    ),
                    TaskPlanItem(
                        task_id="task_sec_3_4",
                        title="Soạn thảo Mục 3 & 4: Thiết bị, Hóa chất và Quy trình Chi tiết",
                        role=TaskRole.WRITER,
                        provider="mock",
                        model="mock-model",
                        instructions="Quy định nồng độ cồn 70%, hóa chất tẩy rửa, các bước lau từ trên xuống dưới, trong ra ngoài.",
                        dependencies=["task_sec_1_2"],
                        result_format="markdown",
                        acceptance_criteria=["Quy trình chi tiết từng bước", "Cảnh báo an toàn hóa chất"]
                    ),
                    TaskPlanItem(
                        task_id="task_sec_5_6",
                        title="Soạn thảo Mục 5 & 6: Giám sát Vi sinh và Biểu mẫu Hồ sơ",
                        role=TaskRole.WRITER,
                        provider="mock",
                        model="mock-model",
                        instructions="Biểu mẫu kiểm tra vệ sinh hàng ngày, tần suất lấy mẫu đĩa thạch vi sinh bề mặt.",
                        dependencies=["task_sec_3_4"],
                        result_format="markdown",
                        acceptance_criteria=["Có bảng biểu mẫu kiểm tra", "Quy định lưu trữ hồ sơ"]
                    ),
                    TaskPlanItem(
                        task_id="task_review_all",
                        title="Rà soát Chuyên môn và Thẩm định Chất lượng Toàn diện",
                        role=TaskRole.REVIEWER,
                        provider="mock",
                        model="mock-model",
                        instructions="Kiểm tra tính logic, mâu thuẫn thuật ngữ, trích dẫn quy chuẩn và placeholder sót.",
                        dependencies=["task_sec_5_6"],
                        result_format="json",
                        acceptance_criteria=["Điểm chất lượng >= 8.5", "Không có lỗi Critical"]
                    )
                ],
                references_to_consult=[
                    "Thông tư 35/2018/TT-BYT quy định Thực hành tốt sản xuất thuốc (GMP-WHO)",
                    "Dược điển Việt Nam V - Phụ lục kiểm nghiệm vi sinh và môi trường vô trùng",
                    "WHO Technical Report Series, No. 986, Annex 2 (Good Manufacturing Practices)"
                ],
                time_limit_seconds=600.0,
                budget_limit_usd=5.0
            )
            return plan, TokenUsage(prompt_tokens=200, completion_tokens=500, total_tokens=700, estimated_cost_usd=0.001)

        elif schema_cls is ReviewResult or schema_cls.__name__ == "ReviewResult":
            if self.review_approved:
                res = ReviewResult(
                    is_approved=True,
                    score=9.5,
                    critiques=[],
                    summary="Nội dung đạt yêu cầu chuyên môn, logic chặt chẽ, đầy đủ trích dẫn."
                )
            else:
                res = ReviewResult(
                    is_approved=False,
                    score=6.0,
                    critiques=[
                        ReviewCritique(
                            category="citations",
                            severity="WARNING",
                            section_id="sec_1",
                            description="Chưa trích dẫn cụ thể điều khoản Thông tư 35/2018/TT-BYT",
                            suggested_fix="Bổ sung Điều 4 và Phụ lục 1 của Thông tư 35/2018/TT-BYT."
                        )
                    ],
                    summary="Cần bổ sung trích dẫn quy chuẩn bắt buộc."
                )
            return res, TokenUsage(prompt_tokens=150, completion_tokens=150, total_tokens=300, estimated_cost_usd=0.0005)

        # Generic fallback
        return schema_cls(), TokenUsage(prompt_tokens=50, completion_tokens=50, total_tokens=100, estimated_cost_usd=0.0001)

    async def health_check(self) -> bool:
        return True
