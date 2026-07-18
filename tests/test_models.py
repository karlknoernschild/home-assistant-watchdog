"""Model tests for Power Watchdog WiFi."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_MODELS_PATH = (
    Path(__file__).resolve().parent.parent / "power_watchdog_wifi" / "models.py"
)
_SPEC = spec_from_file_location("power_watchdog_wifi.models", _MODELS_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

LegTelemetry = _MODULE.LegTelemetry
WatchdogTelemetry = _MODULE.WatchdogTelemetry
metadata_from_device_row = _MODULE.metadata_from_device_row


def test_total_energy_is_sum_of_legs() -> None:
    telemetry = WatchdogTelemetry(
        leg1=LegTelemetry(
            voltage_v=120.0,
            current_a=10.0,
            power_w=1200.0,
            energy_kwh=1.25,
            frequency_hz=60.0,
            status_raw=0,
            error_raw=0,
        ),
        leg2=LegTelemetry(
            voltage_v=121.0,
            current_a=11.0,
            power_w=1331.0,
            energy_kwh=2.75,
            frequency_hz=60.0,
            status_raw=0,
            error_raw=0,
        ),
    )

    assert telemetry.total_energy_kwh == 4.0


def test_metadata_normalization_uses_stable_fields() -> None:
    metadata = metadata_from_device_row(
        "12345",
        {
            "id": 123,
            "device_no": 12345,
            "gid": "12345",
            "name": "Coach EMS",
            "version": "2.0.0",
            "mcu_version": "1.4.0",
            "connect_type": "wifi",
            "socket_state": 1,
            "start_from": "shore",
        },
    )

    assert metadata.device_no == "12345"
    assert metadata.device_id == "123"
    assert metadata.name == "Coach EMS"
    assert metadata.firmware == "2.0.0"
    assert metadata.mcu_firmware == "1.4.0"
    assert metadata.connect_type == "wifi"
    assert metadata.socket_state == "1"
    assert metadata.start_from == "shore"
    assert metadata.cloud_identifiers == ("123", "12345")
