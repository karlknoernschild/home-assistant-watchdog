"""Read-only decoder for Power Watchdog WiFi telemetry packets."""

from __future__ import annotations

import struct

from .models import LegTelemetry, WatchdogTelemetry

_IDENTIFIER = bytes.fromhex("24797740")
_TAIL = bytes.fromhex("7121")
_REPORT_COMMAND = 0x01
_RECORD_SIZE = 34
PROTOCOL_MARKERS = {
    "identifier_hex": _IDENTIFIER.hex(),
    "tail_hex": _TAIL.hex(),
    "report_command": _REPORT_COMMAND,
    "record_size": _RECORD_SIZE,
}


class ProtocolError(ValueError):
    """Raised when a telemetry packet is malformed."""


def _decode_leg(raw: bytes) -> LegTelemetry:
    # Record size is fixed by protocol reverse engineering; a mismatch means
    # packet corruption, version drift, or a decoder bug.
    if len(raw) != _RECORD_SIZE:
        raise ProtocolError(f"Expected {_RECORD_SIZE} bytes, got {len(raw)}")

    (
        voltage,
        current,
        power,
        energy,
        _unknown_1,
        _unknown_2,
        _backlight,
        _neutral_detection,
        _unknown_3,
        _unknown_4,
        frequency,
        error,
        status,
    ) = struct.unpack(">6i4Bi2B", raw)

    return LegTelemetry(
        voltage_v=voltage / 10_000.0,
        current_a=current / 10_000.0,
        power_w=power / 10_000.0,
        energy_kwh=energy / 10_000.0,
        frequency_hz=frequency / 100.0,
        status_raw=status,
        error_raw=error,
    )


def decode_report(hex_packet: str) -> WatchdogTelemetry | None:
    """Decode a report packet.

    Returns None for valid non-telemetry packets such as heartbeat packets.
    This function only decodes data; it cannot send commands.
    """
    try:
        packet = bytes.fromhex(hex_packet)
    except ValueError as err:
        raise ProtocolError("Packet is not valid hexadecimal") from err

    if len(packet) < 11:
        raise ProtocolError("Packet is too short")
    if packet[:4] != _IDENTIFIER:
        raise ProtocolError("Unexpected packet identifier")
    if packet[-2:] != _TAIL:
        raise ProtocolError("Unexpected packet terminator")

    command = packet[6]
    payload_length = int.from_bytes(packet[7:9], "big")
    payload = packet[9:-2]

    if len(payload) != payload_length:
        raise ProtocolError(
            f"Payload length mismatch: expected {payload_length}, got {len(payload)}"
        )

    if command != _REPORT_COMMAND:
        return None

    if payload_length != _RECORD_SIZE * 2:
        raise ProtocolError(f"Unexpected report length: {payload_length}")

    return WatchdogTelemetry(
        leg1=_decode_leg(payload[:_RECORD_SIZE]),
        leg2=_decode_leg(payload[_RECORD_SIZE:]),
    )
