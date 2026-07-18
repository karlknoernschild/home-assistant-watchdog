#!/usr/bin/env python3
"""Read-only Hughes Power Watchdog WiFi API probe.

This program can call only these two HTTPS GET endpoints:
  * /user/login
  * /device/list

No relay-control, reset, edit, add, delete, share, or other mutation endpoint
is implemented or permitted.
"""

from __future__ import annotations

import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://api.watchdogsrv.com/api"
APP_VERSION = "1.0.15"
DEVICE_TYPE = "android"
ALLOWED_PATHS = frozenset({"/user/login", "/device/list"})


def api_get(path: str, query: dict[str, str]) -> Any:
    if path not in ALLOWED_PATHS:
        raise RuntimeError(f"Blocked non-read-only API path: {path}")

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

    # Do not print the URL: the official login format places the password in
    # the encrypted HTTPS query string.
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(charset)
        return json.loads(payload)


def extract_token(response: Any) -> str | None:
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict) and data.get("token"):
            return str(data["token"])
        if response.get("token"):
            return str(response["token"])
    return None


def main() -> int:
    print("\nHughes Power Watchdog WiFi - read-only probe")
    print("Calls only /user/login and /device/list.")
    print("No device-control or configuration API is implemented.\n")

    account = input("Hughes account email: ").strip()
    password = getpass.getpass("Hughes account password: ")

    if not account or not password:
        print("Email and password are required.", file=sys.stderr)
        return 2

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
        if not token:
            print("Login returned no token. Redacted response:")
            print(json.dumps(login_response, indent=2, ensure_ascii=False))
            return 3

        print("Authentication succeeded. Token was not displayed or saved.")
        print("Requesting device list...")

        device_response = api_get(
            "/device/list",
            {
                "token": token,
                "device": DEVICE_TYPE,
                "version": APP_VERSION,
            },
        )

        output_path = Path(__file__).resolve().with_name(
            "watchdog_device_list.json"
        )
        output_path.write_text(
            json.dumps(device_response, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("\nDevice-list response:")
        print(json.dumps(device_response, indent=2, ensure_ascii=False))
        print(f"\nSaved to: {output_path}")
        print("Review the file before uploading it here.")
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
    except json.JSONDecodeError as exc:
        print(f"\nServer returned invalid JSON: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        password = ""
        token = None


if __name__ == "__main__":
    raise SystemExit(main())
