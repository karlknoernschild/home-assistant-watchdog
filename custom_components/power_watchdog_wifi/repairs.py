"""Repairs issue helpers for Power Watchdog WiFi."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

ISSUE_AUTH_FAILED = "auth_failed"
ISSUE_CANNOT_CONNECT = "cannot_connect"
ISSUE_DEVICE_MAPPING_UNSUPPORTED = "device_mapping_unsupported"


def _issue_id(entry_id: str, issue_key: str) -> str:
    """Build a unique issue id for a config entry."""
    return f"{entry_id}_{issue_key}"


def create_auth_failed_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create/refresh an authentication issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, ISSUE_AUTH_FAILED),
        severity=ir.IssueSeverity.ERROR,
        is_fixable=False,
        translation_key=ISSUE_AUTH_FAILED,
    )


def create_cannot_connect_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create/refresh a connectivity issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, ISSUE_CANNOT_CONNECT),
        severity=ir.IssueSeverity.WARNING,
        is_fixable=False,
        translation_key=ISSUE_CANNOT_CONNECT,
    )


def create_device_mapping_unsupported_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create/refresh a mapping unsupported issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, ISSUE_DEVICE_MAPPING_UNSUPPORTED),
        severity=ir.IssueSeverity.ERROR,
        is_fixable=False,
        translation_key=ISSUE_DEVICE_MAPPING_UNSUPPORTED,
    )


def clear_issue(hass: HomeAssistant, entry_id: str, issue_key: str) -> None:
    """Clear one issue for a config entry."""
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id, issue_key))


def clear_runtime_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Clear issues that can recover during runtime."""
    # Mapping issues are intentionally excluded here because they require user
    # selection/reconfiguration, not transient runtime recovery.
    clear_issue(hass, entry_id, ISSUE_AUTH_FAILED)
    clear_issue(hass, entry_id, ISSUE_CANNOT_CONNECT)
