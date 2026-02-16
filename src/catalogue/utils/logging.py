"""Logging configuration for catalogue domain.

Reuses the same logging patterns as the identity domain.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

import structlog


def get_log_level() -> str:
    """Get log level based on environment."""
    env = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or os.getenv("PROTEAN_ENV") or "development").lower()

    level_map = {
        "production": "INFO",
        "staging": "INFO",
        "development": "DEBUG",
        "test": "WARNING",
    }

    return os.getenv("LOG_LEVEL", level_map.get(env, "INFO"))


def setup_stdlib_logging() -> None:
    """Configure standard library logging."""
    log_level = get_log_level()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "shopstream.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "shopstream_error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def setup_structlog() -> None:
    """Configure structlog for structured logging."""
    env = os.getenv("ENVIRONMENT", "development").lower()

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
    ]

    if env in ["production", "staging"]:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=True,
                    max_frames=2,
                ),
            )
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging() -> None:
    """Configure all logging for the application."""
    setup_stdlib_logging()
    setup_structlog()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """Add context variables that will be included in all subsequent log messages."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()
