#!/usr/bin/env python3
"""Logging utilities for Cloudflare monitoring."""

import logging
import sys
from typing import Any


def setup_logger(
    name: str = "cloudflare",
    level: int = logging.INFO,
    stream: Any = sys.stderr,
) -> logging.Logger:
    """Set up a structured logger for Cloudflare monitoring.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        stream: Output stream (default: stderr)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def get_logger(name: str = "cloudflare") -> logging.Logger:
    """Get an existing logger or create a new one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


class LoggerMixin:
    """Mixin class to provide logging capabilities."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"cloudflare.{self.__class__.__name__}")

    def log_debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)
