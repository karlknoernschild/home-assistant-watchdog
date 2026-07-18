#!/usr/bin/env python3
"""Read-only Hughes Power Watchdog WiFi live decoder probe.

Outbound operations are restricted to:
  - HTTPS GET /api/user/login
  - HTTPS GET /api/device/list
  - WebSocket login
  - WebSocket subscribe

No control, reset, edit, configuration, transfer, or generic command
operation is implemented.
"""

from __future__ import annotations

import getpass
import json
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from websockets.sync.client import connect
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print(
        "Install the required library first:\n\n"
        "    python -m pip install websockets\n",
        file=sys.stderr,
    )
    raise SystemExit(2)

BASE_URL = "https://api.watchdogsrv.com/api"
WS_URL = "ws://ws.watchdogsrv.com:5521/ws"
APP_VERSION = "1.0.15"
DEVICE_TYPE = "android"
CAPTURE_SECONDS = 60

ALLOWED_HTTP_PATHS = frozenset({"/user/login", "/device/list"})
ALLOWED_WS_ACTIONS = frozenset({"login", "subscribe"})

IDENTIFIER = bytes.fromhex("24797740")
TAIL = bytes.fromhex("7121")
DL_REPORT_COMMAND = 0x01
DL_RECORD_SIZE = 34


@dataclass(frozen=True)
class LegTelemetry:
    leg: int
    voltage_v: float
    current_a: float
    power_w: float
    energy_kwh: float
    frequency_hz: float
    status_raw: int
    error_raw: int
    backlight_raw: int
    neutral_detection_raw: int
    unknown_temp1_raw: int
    unknown_temp2_raw: int
    unknown_temp3_raw: int
    unknown_temp4_raw: int


def api_get(path: str, query: dict[str, str]) -> Any:
    if path not in ALLOWED_HTTP_PATHS:
        raise RuntimeError(f"Blocked API path: {path}")

    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "PowerWatchdogWiFi/1.0.15 (Android; read-only decoder probe)",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def extract_token(response: Any) -> str:
    try:
        token = response["data"]["token"]
    except (KeyError, TypeError):
        token = None
    if not token:
        raise RuntimeError("Login response did not contain a token.")
    return str(token)


def extract_devices(response: Any) -> list[dict[str, Any]]:
    try:
        rows = response["data"]["rows"]
    except (KeyError, TypeError):
        return []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def ws_message(action: str, **fields: Any) -> str:
    if action not in ALLOWED_WS_ACTIONS:
        raise RuntimeError(f"Blocked WebSocket action: {action}")
    message = {"act": action, "req": str(int(time.time() * 1000))}
    message.update(fields)
    return json.dumps(message, separators=(",", ":"))


def decode_dl_record(raw: bytes, leg: int) -> LegTelemetry:
    if len(raw) != DL_RECORD_SIZE:
        raise ValueError(f"DL record must be {DL_RECORD_SIZE} bytes.")

    (
        input_voltage,
        current,
        power,
        energy,
        temp1,
        temp2,
        backlight,
        neutral_detection,
        temp3,
        temp4,
        frequency,
        error,
        status,
    ) = struct.unpack(">6i4Bi2B", raw)

    return LegTelemetry(
        leg=leg,
        voltage_v=input_voltage / 10_000.0,
        current_a=current / 10_000.0,
        power_w=power / 10_000.0,
        energy_kwh=energy / 10_000.0,
        frequency_hz=frequency / 100.0,
        status_raw=status,
        error_raw=error,
        backlight_raw=backlight,
        neutral_detection_raw=neutral_detection,
        unknown_temp1_raw=temp1,
        unknown_temp2_raw=temp2,
        unknown_temp3_raw=temp3,
        unknown_temp4_raw=temp4,
    )


def decode_packet(hex_packet: str) -> list[LegTelemetry] | None:
    packet = bytes.fromhex(hex_packet)

    # 4-byte identifier + 5-byte header + payload + 2-byte tail.
    if len(packet) < 11 or packet[:4] != IDENTIFIER or packet[-2:] != TAIL:
        return None

    version = packet[4]
    msg_id = packet[5]
    command = packet[6]
    payload_length = int.from_bytes(packet[7:9], "big")
    payload = packet[9:-2]

    if len(payload) != payload_length:
        raise ValueError(
            f"Payload length mismatch: header={payload_length}, actual={len(payload)}"
        )

    # Command 0x02 is the short heartbeat/status packet. It has no DL records.
    if command != DL_REPORT_COMMAND:
        return None

    if payload_length not in (34, 68):
        raise ValueError(f"Unexpected DL payload length: {payload_length}")

    records = []
    for index in range(0, payload_length, DL_RECORD_SIZE):
        records.append(
            decode_dl_record(payload[index:index + DL_RECORD_SIZE], index // 34 + 1)
        )
    return records


def format_reading(records: list[LegTelemetry]) -> str:
    parts = []
    for item in records:
        parts.append(
            f"L{item.leg}: {item.voltage_v:6.2f} V | "
            f"{item.current_a:6.3f} A | "
            f"{item.power_w:7.1f} W | "
            f"{item.frequency_hz:4.1f} Hz | "
            f"{item.energy_kwh:8.2f} kWh | "
            f"status={item.status_raw} error={item.error_raw}"
        )
    if len(records) == 2:
        total = records[0].power_w + records[1].power_w
        parts.append(f"Total power: {total:.1f} W")
    return "\n".join(parts)


def main() -> int:
    print("\nPower Watchdog read-only live decoder")
    print("No device-control or configuration actions exist in this script.\n")

    account = input("Hughes account email: ").strip()
    password = getpass.getpass("Hughes account password: ")
    token = ""

    try:
        login = api_get(
            "/user/login",
            {
                "account": account,
                "password": password,
                "device": DEVICE_TYPE,
                "version": APP_VERSION,
                "token": "",
            },
        )
        token = extract_token(login)

        device_list = api_get(
            "/device/list",
            {
                "token": token,
                "device": DEVICE_TYPE,
                "version": APP_VERSION,
            },
        )
        devices = extract_devices(device_list)
        if not devices:
            raise RuntimeError("No Watchdog devices were returned.")

        device = devices[0]
        device_no = str(device.get("device_no", "")).strip()
        if not device_no:
            raise RuntimeError("Device list did not include device_no.")

        print(f"\nConnected account device: {device.get('name', '(unnamed)')}")
        print(f"Listening for decoded telemetry for {CAPTURE_SECONDS} seconds...\n")

        output_path = Path(__file__).resolve().with_name(
            "watchdog_decoded_capture.jsonl"
        )
        decoded_rows: list[dict[str, Any]] = []

        with connect(
            WS_URL,
            open_timeout=20,
            close_timeout=5,
            compression="deflate",
            user_agent_header=(
                "PowerWatchdogWiFi/1.0.15 (Android; read-only decoder probe)"
            ),
        ) as websocket:
            websocket.send(ws_message("login", data={"token": token}))
            subscribed = False
            deadline = time.monotonic() + CAPTURE_SECONDS

            while time.monotonic() < deadline:
                try:
                    raw = websocket.recv(timeout=min(10, deadline - time.monotonic()))
                except TimeoutError:
                    continue
                except ConnectionClosed:
                    break

                text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                try:
                    message = json.loads(text)
                except json.JSONDecodeError:
                    continue

                if message.get("act") == "login" and not subscribed:
                    websocket.send(ws_message("subscribe", gid=device_no))
                    subscribed = True
                    continue

                if message.get("act") != "report":
                    continue

                packet_hex = message.get("data", {}).get("data")
                if not isinstance(packet_hex, str):
                    continue

                records = decode_packet(packet_hex)
                if not records:
                    continue

                timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                print(timestamp)
                print(format_reading(records))
                print()

                decoded_rows.append(
                    {
                        "received_at": timestamp,
                        "legs": [asdict(item) for item in records],
                        "total_power_w": sum(item.power_w for item in records),
                    }
                )

        with output_path.open("w", encoding="utf-8") as output:
            for row in decoded_rows:
                output.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"Saved {len(decoded_rows)} decoded reports to:")
        print(output_path)
        return 0

    except urllib.error.HTTPError as exc:
        print(f"HTTP request failed with status {exc.code}.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Probe failed: {exc}", file=sys.stderr)
        return 1
    finally:
        password = ""
        token = ""


if __name__ == "__main__":
    raise SystemExit(main())
