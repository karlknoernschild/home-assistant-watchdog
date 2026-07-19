"""Read-only cloud client for Power Watchdog WiFi.

This module encapsulates all network communication with the vendor cloud:
- REST login
- REST device listing
- WebSocket login + subscription
- packet decode handoff

Design goals for maintainers:
- Keep the surface area strictly read-only.
- Convert low-level transport/protocol errors into integration-level exceptions.
- Emit decode failures as explicit events so coordinator metrics stay accurate.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType

from .const import API_BASE_URL, APP_DEVICE, APP_VERSION, WS_URL
from .models import WatchdogTelemetryEvent
from .protocol import ProtocolError, decode_report


class WatchdogError(Exception):
    """Base exception."""


class WatchdogAuthError(WatchdogError):
    """Authentication failed."""


class WatchdogConnectionError(WatchdogError):
    """Cloud connection failed."""


class ReadOnlyWatchdogClient:
    """A deliberately read-only client.

    Only login, device listing, WebSocket login and WebSocket subscription
    are implemented. There is no generic request or command method exposed.
    """

    def __init__(
        self,
        session: ClientSession,
        account: str,
        password: str,
    ) -> None:
        self._session = session
        self._account = account
        self._password = password
        self._token: str | None = None

    @property
    def authenticated(self) -> bool:
        """Return whether a token is currently available."""
        return self._token is not None

    async def async_login(self) -> None:
        """Authenticate using the same read operation as the official app."""
        params = {
            "account": self._account,
            "password": self._password,
            "device": APP_DEVICE,
            "version": APP_VERSION,
            "token": "",
        }
        try:
            async with self._session.get(
                f"{API_BASE_URL}/user/login",
                params=params,
                timeout=ClientTimeout(total=30),
            ) as response:
                payload = await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            raise WatchdogConnectionError("Unable to contact Watchdog cloud") from err

        if response.status != 200:
            raise WatchdogConnectionError(f"Login HTTP status {response.status}")
        if payload.get("code") != 200:
            raise WatchdogAuthError(str(payload.get("msg", "Authentication failed")))

        token = payload.get("data", {}).get("token")
        if not token:
            raise WatchdogAuthError("Login response did not include a token")
        self._token = str(token)

    async def async_list_devices(self) -> list[dict[str, Any]]:
        """Return devices belonging to the authenticated account."""
        if not self._token:
            await self.async_login()

        params = {
            "token": self._token,
            "device": APP_DEVICE,
            "version": APP_VERSION,
        }
        try:
            async with self._session.get(
                f"{API_BASE_URL}/device/list",
                params=params,
                timeout=ClientTimeout(total=30),
            ) as response:
                payload = await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            raise WatchdogConnectionError("Unable to retrieve device list") from err

        if response.status != 200 or payload.get("code") != 200:
            raise WatchdogConnectionError(str(payload.get("msg", "Device list failed")))

        rows = payload.get("data", {}).get("rows", [])
        return [row for row in rows if isinstance(row, dict)]

    async def async_telemetry(
        self,
        device_no: str,
    ) -> AsyncIterator[WatchdogTelemetryEvent]:
        """Yield live telemetry from a read-only cloud subscription."""
        for attempt in range(2):
            if not self._token:
                await self.async_login()
            assert self._token is not None

            try:
                async with self._session.ws_connect(
                    WS_URL,
                    heartbeat=30,
                    timeout=ClientTimeout(total=30),
                ) as websocket:
                    await websocket.send_json(
                        {
                            "act": "login",
                            "req": str(int(time.time() * 1000)),
                            "data": {"token": self._token},
                        }
                    )
                    subscribed = False

                    async for message in websocket:
                        if message.type == WSMsgType.TEXT:
                            try:
                                payload = json.loads(message.data)
                            except (json.JSONDecodeError, TypeError):
                                continue

                            action = payload.get("act")
                            if action == "login" and not subscribed:
                                if payload.get("data", {}).get("res") != 1:
                                    # Retry once with a fresh token when the
                                    # cached token is no longer accepted.
                                    if attempt == 0:
                                        self._token = None
                                        break
                                    raise WatchdogAuthError("WebSocket login rejected")
                                await websocket.send_json(
                                    {
                                        "act": "subscribe",
                                        "req": str(int(time.time() * 1000)),
                                        "gid": device_no,
                                    }
                                )
                                subscribed = True
                                continue

                            # We intentionally ignore non-report actions here; those
                            # frames are control/keepalive noise for telemetry flow.
                            if action != "report":
                                continue

                            packet = payload.get("data", {}).get("data")
                            if not isinstance(packet, str):
                                continue
                            try:
                                decoded = decode_report(packet)
                            except ProtocolError:
                                # Decode errors are surfaced as explicit events so
                                # coordinator counters/diagnostics can track them.
                                yield WatchdogTelemetryEvent(
                                    telemetry=None,
                                    decode_error=True,
                                )
                                continue
                            if decoded is not None:
                                yield WatchdogTelemetryEvent(telemetry=decoded)

                        elif message.type in {
                            WSMsgType.CLOSED,
                            WSMsgType.CLOSE,
                            WSMsgType.CLOSING,
                            WSMsgType.ERROR,
                        }:
                            break
                    else:
                        continue

                    if attempt == 0 and self._token is None:
                        continue
                    return
            except WatchdogError:
                raise
            except (TimeoutError, ClientError) as err:
                raise WatchdogConnectionError("Telemetry connection failed") from err
