"""Structured application logging with secret masking."""

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from barsa.core.config import Settings

# Regex patterns matching potential secret tokens, keys, passwords, and authorization headers
SECRET_PATTERNS = [
    (re.compile(r"Bearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(api[_-]?key|secret|token|password|auth|authorization)\s*[:=]\s*([^\s,;]+)",
            re.IGNORECASE,
        ),
        r"\1: [REDACTED]",
    ),
]


def redact_sensitive_data(message: str) -> str:
    """Mask credentials and secrets from log messages."""
    redacted = message
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class SafeTextFormatter(logging.Formatter):
    """Text log formatter that masks secrets from log outputs."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return redact_sensitive_data(formatted)


class StructuredJsonFormatter(logging.Formatter):
    """Structured JSON formatter for production and cloud-ready log collection."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_data(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include structured extra attributes if present
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                if k not in log_entry:
                    log_entry[k] = v

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(settings: Settings) -> None:
    """Configure root and barsa logging handlers according to settings."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # Clear existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)

    if settings.log_json_format:
        formatter: logging.Formatter = StructuredJsonFormatter()
    else:
        formatter = SafeTextFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure uvicorn loggers to use the same level
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.handlers = [console_handler]
        u_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance for the given module name."""
    return logging.getLogger(f"barsa.{name}" if not name.startswith("barsa") else name)
