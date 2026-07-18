"""Protocol decoder tests."""

from __future__ import annotations

import struct
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "power_watchdog_wifi"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [  # type: ignore[attr-defined]
        str(ROOT / "custom_components" / PACKAGE_NAME)
    ]
    sys.modules[PACKAGE_NAME] = package

models = _load_module(
    "power_watchdog_wifi.models",
    ROOT / "custom_components" / "power_watchdog_wifi" / "models.py",
)
protocol = _load_module(
    "power_watchdog_wifi.protocol",
    ROOT / "custom_components" / "power_watchdog_wifi" / "protocol.py",
)


def _encode_leg(
    voltage: int = 1200000,
    current: int = 100000,
    power: int = 1200000,
    energy: int = 12500,
    frequency: int = 6000,
    error: int = 0,
    status: int = 0,
) -> bytes:
    return struct.pack(
        ">6i4Bi2B",
        voltage,
        current,
        power,
        energy,
        0,
        0,
        0,
        0,
        0,
        0,
        frequency,
        error,
        status,
    )


def _build_packet(command: int = 0x01, payload: bytes | None = None) -> str:
    if payload is None:
        payload = _encode_leg() + _encode_leg()
    packet = (
        bytes.fromhex("24797740")
        + bytes([1, 1, command])
        + len(payload).to_bytes(2, "big")
        + payload
        + bytes.fromhex("7121")
    )
    return packet.hex()


def test_decode_report_decodes_valid_payload() -> None:
    decoded = protocol.decode_report(_build_packet())
    assert decoded is not None
    assert decoded.total_energy_kwh == 2.5
    assert decoded.total_power_w == 240.0


def test_decode_report_returns_none_for_non_telemetry_command() -> None:
    decoded = protocol.decode_report(_build_packet(command=0x09))
    assert decoded is None


def test_decode_report_rejects_payload_length_mismatch() -> None:
    payload = _encode_leg() + _encode_leg()
    packet = (
        bytes.fromhex("24797740")
        + bytes([1, 1, 0x01])
        + (len(payload) + 1).to_bytes(2, "big")
        + payload
        + bytes.fromhex("7121")
    )

    try:
        protocol.decode_report(packet.hex())
    except protocol.ProtocolError as err:
        assert "Payload length mismatch" in str(err)
    else:
        raise AssertionError("Expected ProtocolError for payload mismatch")
