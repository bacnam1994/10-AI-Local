"""Base Provider Adapter Interface for Multi-Cloud AI Integration."""

from abc import ABC, abstractmethod
from typing import TypeVar, Type, Optional, Any
from pydantic import BaseModel
import httpx

from app.core.models import TokenUsage
from app.config.settings import settings

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Base exception for AI provider operations."""
    def __init__(self, message: str, status_code: Optional[int] = None, is_transient: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_transient = is_transient


class AuthenticationError(ProviderError):
    """Raised when API key is missing or invalid."""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded (HTTP 429)."""
    def __init__(self, message: str, retry_after: float = 5.0):
        super().__init__(message, status_code=429, is_transient=True)
        self.retry_after = retry_after


class QuotaExceededError(ProviderError):
    """Raised when account balance or quota is exhausted."""
    pass


class TimeoutError(ProviderError):
    """Raised when HTTP request times out."""
    def __init__(self, message: str = "Request to AI provider timed out"):
        super().__init__(message, status_code=408, is_transient=True)


class BaseProviderAdapter(ABC):
    """Abstract Base Class for all AI Provider Adapters."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = ""):
        self.api_key = api_key or ""
        self.default_model = default_model

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that provider configuration (API key, model) is present and plausible."""
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return list of officially supported models for this provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 90.0,
    ) -> tuple[str, TokenUsage]:
        """Send prompt to the AI provider and return textual response and token usage."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 90.0,
    ) -> tuple[T, TokenUsage]:
        """Generate structured JSON adhering to the provided Pydantic model class."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Perform a low-cost connectivity check to verify API key and network health."""
        pass

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on model pricing table."""
        rates = settings.price_table.get(model, (1.00, 3.00))
        prompt_cost = (prompt_tokens / 1_000_000) * rates[0]
        completion_cost = (completion_tokens / 1_000_000) * rates[1]
        return round(prompt_cost + completion_cost, 6)

    def normalize_error(self, exc: Exception) -> ProviderError:
        """Standardize exceptions across all HTTP and provider libraries."""
        if isinstance(exc, ProviderError):
            return exc
        if isinstance(exc, httpx.TimeoutException):
            return TimeoutError(f"HTTP Timeout connecting to provider: {str(exc)}")
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            try:
                err_json = exc.response.json()
                if isinstance(err_json, dict) and "error" in err_json:
                    err_obj = err_json["error"]
                    if isinstance(err_obj, dict):
                        text = err_obj.get("message", exc.response.text)
                    else:
                        text = str(err_obj)
                else:
                    text = exc.response.text
            except Exception:
                text = exc.response.text

            if status in (401, 403):
                return AuthenticationError(f"Xác thực thất bại (Mã {status}): {text}")
            if status == 404:
                return ProviderError(f"Không tìm thấy endpoint hoặc mô hình (Mã 404): {text}", status_code=404)
            if status == 429:
                retry_after = 5.0
                if "retry-after" in exc.response.headers:
                    try:
                        retry_after = float(exc.response.headers["retry-after"])
                    except ValueError:
                        pass
                return RateLimitError(f"Vượt hạn mức yêu cầu / Hết hạn ngạch (Mã 429): {text}", retry_after=retry_after)
            if status >= 500:
                return ProviderError(f"Máy chủ nhà cung cấp gặp sự cố (Mã {status}): {text}", status_code=status, is_transient=True)
            return ProviderError(f"Lỗi phản hồi HTTP (Mã {status}): {text}", status_code=status)
        return ProviderError(f"Lỗi kết nối hoặc ngoại lệ: {str(exc)}")
