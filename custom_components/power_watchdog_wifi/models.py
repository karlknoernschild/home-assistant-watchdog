"""Data models for Power Watchdog WiFi."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class LegTelemetry:
    """Telemetry for one 120 V leg."""

    voltage_v: float
    current_a: float
    power_w: float
    energy_kwh: float
    frequency_hz: float
    status_raw: int
    error_raw: int


@dataclass(frozen=True, slots=True)
class WatchdogTelemetry:
    """Decoded telemetry for both legs."""

    leg1: LegTelemetry
    leg2: LegTelemetry

    @property
    def total_power_w(self) -> float:
        """Return total real power."""
        return self.leg1.power_w + self.leg2.power_w

    @property
    def total_current_a(self) -> float:
        """Return the sum of both leg currents."""
        return self.leg1.current_a + self.leg2.current_a

    @property
    def total_energy_kwh(self) -> float:
        """Return accumulated energy across both legs."""
        return self.leg1.energy_kwh + self.leg2.energy_kwh

    @property
    def frequency_hz(self) -> float:
        """Return line frequency."""
        return self.leg1.frequency_hz


@dataclass(frozen=True, slots=True)
class WatchdogTelemetryEvent:
    """One decoded telemetry packet event."""

    telemetry: WatchdogTelemetry | None
    decode_error: bool = False


@dataclass(frozen=True, slots=True)
class WatchdogDeviceMetadata:
    """Normalized device metadata from the cloud list endpoint."""

    device_no: str
    device_id: str | None = None
    name: str | None = None
    firmware: str | None = None
    mcu_firmware: str | None = None
    connect_type: str | None = None
    socket_state: str | None = None
    start_from: str | None = None
    cloud_identifiers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WatchdogSnapshot:
    """Coordinator runtime snapshot."""

    latest_telemetry: WatchdogTelemetry | None = None
    last_telemetry_timestamp: datetime | None = None
    reconnect_count: int = 0
    decode_error_count: int = 0
    packet_count: int = 0
    last_connection_error: str | None = None
    last_successful_connect_timestamp: datetime | None = None
    device_metadata: WatchdogDeviceMetadata | None = None
    last_device_refresh_timestamp: datetime | None = None
    native_today_energy_available: bool = False
    native_yesterday_energy_available: bool = False
    native_peak_demand_available: bool = False
    derived_today_energy_kwh: float | None = None
    derived_yesterday_energy_kwh: float | None = None
    derived_rolling_average_power_w: float | None = None


@dataclass(frozen=True, slots=True)
class WatchdogDerivedEnergyState:
    """Persisted state for derived daily energy counters."""

    day_iso: str
    day_start_total_energy_kwh: float
    today_energy_kwh: float
    yesterday_energy_kwh: float


def _optional_string(value: Any) -> str | None:
    """Normalize optional values to strings."""
    if value is None:
        return None
    return str(value)


def metadata_from_device_row(
    device_no: str,
    device: Mapping[str, Any],
) -> WatchdogDeviceMetadata:
    """Normalize metadata fields from a device list row."""
    cloud_identifiers: list[str] = []
    for key in ("id", "device_no", "gid"):
        value = device.get(key)
        if value is None:
            continue
        normalized = str(value)
        if normalized and normalized not in cloud_identifiers:
            cloud_identifiers.append(normalized)

    return WatchdogDeviceMetadata(
        device_no=device_no,
        device_id=_optional_string(device.get("id")),
        name=_optional_string(device.get("name")),
        firmware=_optional_string(device.get("version")),
        mcu_firmware=_optional_string(device.get("mcu_version")),
        connect_type=_optional_string(device.get("connect_type")),
        socket_state=_optional_string(device.get("socket_state")),
        start_from=_optional_string(device.get("start_from")),
        cloud_identifiers=tuple(cloud_identifiers),
    )
