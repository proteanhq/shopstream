"""Logging configuration for the Payments domain."""

import logging

import structlog

logger = structlog.get_logger(__name__)

# Suppress noisy library loggers
logging.getLogger("protean").setLevel(logging.WARNING)
