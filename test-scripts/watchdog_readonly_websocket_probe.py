#!/usr/bin/env python3
"""Read-only Hughes Power Watchdog WiFi WebSocket probe.

Permitted outbound operations:
  1. HTTPS GET /api/user/login
  2. HTTPS GET /api/device/list
  3. WebSocket action "login"
  4. WebSocket action "subscribe"

The script contains no relay-control, reset, edit, add, delete, sharing,
configuration, transfer, or device-command implementation.
"""

from __future__ import annotations

import getpass
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from websockets.sync.client import connect
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print(
        "The 'websockets' package is not installed.\n"
        "Run this command, then try again:\n\n"
        "    python -m pip install websockets\n",
        file=sys.stderr,
    )
    raise SystemExit(2)

BASE_URL = "https://api.watchdogsrv.com/api"
WS_URL = "ws://ws.watchdogsrv.com:5521/ws"
APP_VERSION = "1.0.15"
DEVICE_TYPE = "android"

ALLOWED_HTTP_PATHS = frozenset({"/user/login", "/device/list"})
ALLOWED_WS_ACTIONS = frozenset({"login", "subscribe"})
CAPTURE_SECONDS = 45


def api_get(path: str, query: dict[str, str]) -> Any:
    if path not in ALLOWED_HTTP_PATHS:
        raise RuntimeError(f"Blocked API path: {path}")

    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "PowerWatchdogWiFi/1.0.15 "
                "(Android; read-only interoperability probe)"
            ),
        },
    )

    # Never print the URL because the official login format places the
    # password in the encrypted HTTPS query string.
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def extract_token(response: Any) -> str:
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict) and data.get("token"):
            return str(data["token"])
    raise RuntimeError("Login response did not contain a token.")


def extract_devices(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    data = response.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def make_ws_message(action: str, **fields: Any) -> str:
    if action not in ALLOWED_WS_ACTIONS:
        raise RuntimeError(f"Blocked WebSocket action: {action}")

    message: dict[str, Any] = {
        "act": action,
        "req": str(int(time.time() * 1000)),
    }
    message.update(fields)
    return json.dumps(message, separators=(",", ":"))


def redact(value: Any, token: str) -> Any:
    if isinstance(value, str):
        return value.replace(token, "<REDACTED_TOKEN>")
    if isinstance(value, list):
        return [redact(item, token) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, token) for key, item in value.items()}
    return value


def main() -> int:
    print("\nHughes Power Watchdog WiFi - read-only telemetry probe")
    print("Allowed outbound actions: login, device list, WebSocket login, subscribe.")
    print("No device-control or configuration operation is implemented.\n")

    account = input("Hughes account email: ").strip()
    password = getpass.getpass("Hughes account password: ")

    if not account or not password:
        print("Email and password are required.", file=sys.stderr)
        return 2

    token = ""
    try:
        print("\nAuthenticating...")
        login_response = api_get(
            "/user/login",
            {
                "account": account,
                "password": password,
                "device": DEVICE_TYPE,
                "version": APP_VERSION,
                "token": "",
            },
        )
        token = extract_token(login_response)
        print("Authentication succeeded. Token will not be displayed or saved.")

        print("Retrieving device list...")
        device_response = api_get(
            "/device/list",
            {
                "token": token,
                "device": DEVICE_TYPE,
                "version": APP_VERSION,
            },
        )
        devices = extract_devices(device_response)
        if not devices:
            raise RuntimeError("No devices were returned by /device/list.")

        if len(devices) == 1:
            device = devices[0]
        else:
            print("\nDevices:")
            for index, item in enumerate(devices, start=1):
                print(f"  {index}. {item.get('name', '(unnamed)')}")
            selected = int(input("Select device number: ").strip())
            device = devices[selected - 1]

        device_name = str(device.get("name", "(unnamed)"))
        device_no = str(device.get("device_no", "")).strip()
        if not device_no:
            raise RuntimeError("Selected device has no device_no value.")

        print(f"Selected: {device_name}")
        print(f"Connecting to {WS_URL}...")
        print(f"Listening for up to {CAPTURE_SECONDS} seconds.\n")

        output_path = Path(__file__).resolve().with_name(
            "watchdog_websocket_capture.jsonl"
        )
        records: list[dict[str, Any]] = []

        with connect(
            WS_URL,
            open_timeout=20,
            close_timeout=5,
            compression="deflate",
            user_agent_header=(
                "PowerWatchdogWiFi/1.0.15 "
                "(Android; read-only interoperability probe)"
            ),
        ) as websocket:
            login_message = make_ws_message(
                "login",
                data={"token": token},
            )
            websocket.send(login_message)
            print("Sent read-only WebSocket login.")

            deadline = time.monotonic() + CAPTURE_SECONDS
            subscribed = False

            while time.monotonic() < deadline:
                remaining = max(0.1, deadline - time.monotonic())
                try:
                    raw = websocket.recv(timeout=min(10.0, remaining))
                except TimeoutError:
                    print("Waiting for telemetry...")
                    continue
                except ConnectionClosed as exc:
                    print(f"WebSocket closed: {exc}")
                    break

                timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                text = (
                    raw.decode("utf-8", errors="replace")
                    if isinstance(raw, bytes)
                    else str(raw)
                )

                try:
                    parsed: Any = json.loads(text)
                except json.JSONDecodeError:
                    parsed = text

                safe = redact(parsed, token)
                record = {
                    "received_at": timestamp,
                    "message": safe,
                }
                records.append(record)

                print("Received:")
                print(json.dumps(safe, indent=2, ensure_ascii=False))

                # The official app subscribes after WebSocket login succeeds.
                # The subscription key is the device_no value returned by
                # /device/list.
                if not subscribed:
                    action = parsed.get("act") if isinstance(parsed, dict) else None
                    if action == "login":
                        subscribe_message = make_ws_message(
                            "subscribe",
                            gid=device_no,
                        )
                        websocket.send(subscribe_message)
                        subscribed = True
                        print("\nSent read-only subscription for the selected device.\n")

        with output_path.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"\nSaved {len(records)} received messages to:")
        print(output_path)
        print("\nReview that file, then upload it here.")
        return 0

    except urllib.error.HTTPError as exc:
        print(f"\nHTTP request failed with status {exc.code}.", file=sys.stderr)
        try:
            body = exc.read().decode("utf-8", errors="replace")
            if body:
                print(f"Server response: {body}", file=sys.stderr)
        except Exception:
            pass
        return 1
    except urllib.error.URLError as exc:
        print(f"\nNetwork request failed: {exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nProbe failed: {exc}", file=sys.stderr)
        return 1
    finally:
        password = ""
        token = ""


if __name__ == "__main__":
    raise SystemExit(main())
