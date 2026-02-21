"""Logging configuration for the Reviews domain."""

import structlog


def get_logger(name: str):
    return structlog.get_logger(name)
