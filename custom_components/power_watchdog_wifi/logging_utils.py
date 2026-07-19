"""Logging configuration helpers for Power Watchdog WiFi."""

from __future__ import annotations

import logging

from .const import (
    DEFAULT_LOG_LEVEL,
    DOMAIN,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_INHERIT,
    LOG_LEVEL_WARNING,
)

_LOGGER = logging.getLogger(__name__)

_LOG_LEVEL_TO_PYTHON: dict[str, int | None] = {
    LOG_LEVEL_INHERIT: None,
    LOG_LEVEL_DEBUG: logging.DEBUG,
    LOG_LEVEL_INFO: logging.INFO,
    LOG_LEVEL_WARNING: logging.WARNING,
    LOG_LEVEL_ERROR: logging.ERROR,
}


def apply_package_log_level(level_name: str | None) -> str:
    """Apply logger level to the integration package logger.

    Returns the normalized level key that was applied.
    """
    normalized = str(level_name or DEFAULT_LOG_LEVEL).lower()
    if normalized not in _LOG_LEVEL_TO_PYTHON:
        normalized = DEFAULT_LOG_LEVEL

    package_logger = logging.getLogger(f"custom_components.{DOMAIN}")
    level_value = _LOG_LEVEL_TO_PYTHON[normalized]

    if level_value is None:
        # "inherit" means honour whatever level HA's logger component has
        # already applied to this logger.  Calling setLevel(NOTSET) here would
        # silently clear any level set by configuration.yaml, so we leave the
        # logger untouched and let Python's hierarchy propagation do its work.
        _LOGGER.debug("Integration log level: inherit; HA logger config unchanged")
    else:
        package_logger.setLevel(level_value)
        _LOGGER.debug("Applied integration log level: %s", normalized)
    return normalized
