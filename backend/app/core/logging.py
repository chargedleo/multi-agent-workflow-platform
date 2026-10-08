import logging
import re
import sys
from typing import Optional

SENSITIVE_PATTERNS = [
    (re.compile(r"(password[:=]\s*)[^\s&,;'\"]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE), r"\1***"),
    (re.compile(r"((?:api[_-]?key|token)[:=]\s*)[^\s&,;'\"]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(postgresql(?:\+asyncpg)?://[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1***\3"),
    (re.compile(r"(sk-[a-zA-Z0-9]{8,})", re.IGNORECASE), r"sk-***"),
]


def sanitize_log_msg(message: str) -> str:
    """Sanitize message to ensure credentials, passwords, or tokens are masked."""
    if not isinstance(message, str):
        return str(message)
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


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


def format_log_msg(
    message: str,
    request_id: Optional[str] = None,
    run_id: Optional[str] = None,
    req_id: Optional[str] = None,
) -> str:
    """Helper to prefix messages with request ID and/or run ID without leaking secrets."""
    sanitized = sanitize_log_msg(message)
    actual_req = request_id or req_id
    prefixes = []
    if actual_req:
        prefixes.append(f"req:{actual_req}")
    if run_id:
        prefixes.append(f"run:{run_id}")
    if prefixes:
        prefix_str = " ".join(f"[{p}]" for p in prefixes)
        return f"{prefix_str} {sanitized}"
    return sanitized

