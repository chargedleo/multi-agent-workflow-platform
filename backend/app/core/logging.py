"""Logging configuration for Multi-Agent AI Workflow Automation Platform.

Provides standardized logging formats and request context logging without
exposing credentials or sensitive user data.
"""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO") -> None:
    """Configure the root logger with clean formatting."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Format includes timestamp, level, logger name, and message
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Avoid duplicate handlers if setup_logging is called multiple times
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Quiet overly verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with the given module name."""
    return logging.getLogger(name)


def format_log_msg(message: str, request_id: Optional[str] = None) -> str:
    """Helper to prefix messages with request ID when available."""
    if request_id:
        return f"[{request_id}] {message}"
    return message
