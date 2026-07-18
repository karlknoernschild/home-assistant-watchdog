"""Data models for Power Watchdog WiFi."""

from __future__ import annotations

from dataclasses import dataclass


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
