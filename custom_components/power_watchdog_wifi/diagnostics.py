"""Diagnostics support for Power Watchdog WiFi."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import WatchdogConfigEntry
from .const import CONF_ACCOUNT, CONF_DEVICE_ID, CONF_DEVICE_NO, CONF_PASSWORD
from .protocol import PROTOCOL_MARKERS

_REDACT_KEYS = {
    CONF_ACCOUNT,
    CONF_PASSWORD,
    "token",
    CONF_DEVICE_NO,
    CONF_DEVICE_ID,
    "id",
    "identifiers",
    "cloud_identifiers",
}


def _snapshot_to_dict(snapshot) -> dict[str, Any]:
    """Convert coordinator snapshot to serializable diagnostics data."""
    # Keep this payload schema stable and explicit: HA diagnostics are often
    # copied into bug reports and should be predictable across versions.
    return {
        "latest_telemetry": (
            asdict(snapshot.latest_telemetry)
            if snapshot.latest_telemetry is not None
            else None
        ),
        "last_telemetry_timestamp": (
            snapshot.last_telemetry_timestamp.isoformat()
            if snapshot.last_telemetry_timestamp is not None
            else None
        ),
        "reconnect_count": snapshot.reconnect_count,
        "decode_error_count": snapshot.decode_error_count,
        "packet_count": snapshot.packet_count,
        "last_connection_error": snapshot.last_connection_error,
        "last_successful_connect_timestamp": (
            snapshot.last_successful_connect_timestamp.isoformat()
            if snapshot.last_successful_connect_timestamp is not None
            else None
        ),
        "device_metadata": (
            asdict(snapshot.device_metadata)
            if snapshot.device_metadata is not None
            else None
        ),
        "last_device_refresh_timestamp": (
            snapshot.last_device_refresh_timestamp.isoformat()
            if snapshot.last_device_refresh_timestamp is not None
            else None
        ),
        "native_today_energy_available": snapshot.native_today_energy_available,
        "native_yesterday_energy_available": snapshot.native_yesterday_energy_available,
        "native_peak_demand_available": snapshot.native_peak_demand_available,
        "derived_today_energy_kwh": snapshot.derived_today_energy_kwh,
        "derived_yesterday_energy_kwh": snapshot.derived_yesterday_energy_kwh,
        "derived_rolling_average_power_w": snapshot.derived_rolling_average_power_w,
    }


def _build_diagnostics_payload(entry: WatchdogConfigEntry) -> dict[str, Any]:
    """Build diagnostics payload for config entry or device diagnostics."""
    runtime = entry.runtime_data
    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "runtime": {
            "snapshot": _snapshot_to_dict(runtime.coordinator.data),
            "authenticated": runtime.client.authenticated,
        },
        "energy_source_availability": {
            # Native fields are currently absent in protocol/API paths; these
            # flags make that status explicit in diagnostics output.
            "native_today_energy": False,
            "native_yesterday_energy": False,
            "native_peak_demand": False,
            "derived_metrics_enabled": True,
            "day_rollover_rule": (
                "At local day boundary, today's derived energy rolls into "
                "yesterday and today resets to 0 kWh"
            ),
            "restart_restore_strategy": (
                "Daily derived buckets are restored from persisted state; "
                "rolling-average power resumes from new runtime samples"
            ),
        },
        "protocol_markers": PROTOCOL_MARKERS,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    payload = _build_diagnostics_payload(entry)
    return async_redact_data(payload, _REDACT_KEYS)


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    payload = _build_diagnostics_payload(entry)
    payload["device"] = {
        "id": device.id,
        "identifiers": list(device.identifiers),
    }
    return async_redact_data(payload, _REDACT_KEYS)
