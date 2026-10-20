"""Application Settings and Configuration Management."""

import os
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = BASE_DIR / "app"
PROMPTS_DIR = BASE_DIR / "prompts"
TEMPLATES_DIR = BASE_DIR / "templates"
DEFAULT_JOBS_DIR = BASE_DIR / "jobs"
DEFAULT_OUTPUTS_DIR = BASE_DIR / "outputs"
DEFAULT_LOGS_DIR = BASE_DIR / "logs"
DEFAULT_DB_PATH = BASE_DIR / "jobs" / "orchestrator.sqlite3"

# Ensure runtime directories exist
DEFAULT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    """Global configuration settings for Local Command Bot."""
    app_name: str = "Local Command Bot"
    app_version: str = "1.0.0"
    
    # Paths
    base_dir: Path = BASE_DIR
    jobs_dir: Path = DEFAULT_JOBS_DIR
    outputs_dir: Path = DEFAULT_OUTPUTS_DIR
    logs_dir: Path = DEFAULT_LOGS_DIR
    db_path: Path = DEFAULT_DB_PATH
    
    # Execution defaults
    default_max_concurrency: int = 3
    default_max_retries: int = 3
    default_timeout_seconds: float = 90.0
    default_budget_limit_usd: float = 5.0
    max_review_rounds: int = 1  # Streamlined: single targeted repair if defect detected
    
    # Streamlined Pipeline Defaults: Local AI (Ollama) -> Cloud AI (OmniRoute) -> DOCX
    default_planner_provider: str = "ollama"
    default_planner_model: str = "llama3.1"
    default_writer_provider: str = "omniroute"
    default_writer_model: str = "auto"
    omniroute_base_url: str = "http://localhost:20128/v1"
    ollama_base_url: str = "http://localhost:11434/v1"
    
    # Price table (estimated USD per 1M tokens - prompt / completion)
    price_table: dict[str, tuple[float, float]] = Field(
        default_factory=lambda: {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "claude-3-5-sonnet-20241022": (3.00, 15.00),
            "claude-3-5-haiku-20241022": (0.80, 4.00),
            "gemini-1.5-pro": (1.25, 5.00),
            "gemini-1.5-flash": (0.075, 0.30),
            "gemini-2.0-flash": (0.10, 0.40),
            "llama-3.3-70b-versatile": (0.59, 0.79),
            "llama-3.1-8b-instant": (0.05, 0.08),
            "mixtral-8x7b-32768": (0.24, 0.24),
            "deepseek-chat": (0.14, 0.28),
            "deepseek-reasoner": (0.55, 2.19),
            "mock-model": (0.00, 0.00),
        }
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


# Singleton instance
settings = AppSettings()
