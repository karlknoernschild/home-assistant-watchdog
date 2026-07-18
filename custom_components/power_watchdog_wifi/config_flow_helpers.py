"""Pure helper functions for config-flow device selection."""

from __future__ import annotations

from typing import Any


def build_device_options(devices: list[dict[str, Any]]) -> dict[str, str]:
    """Build the config-flow selector options from discovered devices."""
    return {
        str(item.get("device_no")): str(item.get("name") or item.get("device_no"))
        for item in devices
    }


def find_device_by_device_no(
    devices: list[dict[str, Any]],
    selected_device_no: str,
) -> dict[str, Any]:
    """Return the selected device row by device_no."""
    # This is intentionally strict instead of returning a default/fallback so
    # config flow issues surface clearly when stale selections occur.
    for item in devices:
        if str(item.get("device_no")) == selected_device_no:
            return item
    raise ValueError(f"Unknown device_no selected: {selected_device_no}")
