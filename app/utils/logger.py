"""Application wide logging utilities."""
from __future__ import annotations

import logging
from logging import Logger
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logger(name: str = "lawerai", level: int = logging.INFO) -> Logger:
    """Configure and return a structured logger for the application."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def get_logger(name: Optional[str] = None) -> Logger:
    """Retrieve a configured logger, defaulting to the root application logger."""
    return configure_logger(name or "lawerai")
