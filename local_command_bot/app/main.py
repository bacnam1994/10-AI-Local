"""Main Application Entry Point for Local Command Bot."""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import DARK_STYLESHEET
from app.security.sanitizer import SensitiveDataFilter
from app.config.settings import settings


def setup_application_logging():
    """Configure root logger with SensitiveDataFilter to protect secret credentials."""
    log_dir = settings.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    ch.addFilter(SensitiveDataFilter())
    root_logger.addHandler(ch)

    # File Handler
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    fh.addFilter(SensitiveDataFilter())
    root_logger.addHandler(fh)


def main():
    """Bootstrap Qt Application."""
    setup_application_logging()
    logger = logging.getLogger("app.main")
    logger.info("Khởi động ứng dụng Local Command Bot...")

    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setApplicationVersion(settings.app_version)
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
