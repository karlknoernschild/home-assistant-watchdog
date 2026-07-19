"""API client behavior tests."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from enum import Enum
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    """Load a module from path without importing package side effects."""
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

if "aiohttp" not in sys.modules:
    aiohttp = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    class ClientSession:
        pass

    class ClientTimeout:
        def __init__(self, total: int):
            self.total = total

    class WSMsgType(Enum):
        TEXT = "TEXT"
        CLOSED = "CLOSED"
        CLOSE = "CLOSE"
        CLOSING = "CLOSING"
        ERROR = "ERROR"

    aiohttp.ClientError = ClientError
    aiohttp.ClientSession = ClientSession
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.WSMsgType = WSMsgType
    sys.modules["aiohttp"] = aiohttp

models = _load_module(
    "power_watchdog_wifi.models",
    ROOT / "custom_components" / "power_watchdog_wifi" / "models.py",
)
api = _load_module(
    "power_watchdog_wifi.api",
    ROOT / "custom_components" / "power_watchdog_wifi" / "api.py",
)


class _FakeWsMessage:
    def __init__(self, msg_type: WSMsgType, data: str) -> None:
        self.type = msg_type
        self.data = data


class _FakeWebSocket:
    def __init__(self, messages: list[_FakeWsMessage]) -> None:
        self._messages = messages
        self._index = 0
        self.sent: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        msg = self._messages[self._index]
        self._index += 1
        return msg


class _FakeSession:
    def __init__(self, websockets: list[_FakeWebSocket]) -> None:
        self._websockets = websockets
        self._ws_index = 0

    def ws_connect(self, *_args, **_kwargs):
        ws = self._websockets[self._ws_index]
        self._ws_index += 1
        return ws


class _ClientWithStubLogin(api.ReadOnlyWatchdogClient):
    def __init__(self, session, account, password):
        super().__init__(session, account, password)
        self.login_calls = 0

    async def async_login(self) -> None:
        self.login_calls += 1
        self._token = f"fresh-token-{self.login_calls}"


def test_async_telemetry_reauths_once_after_ws_token_reject(monkeypatch) -> None:
    """WebSocket token rejection should trigger one token refresh + retry."""

    reject_login = _FakeWsMessage(
        WSMsgType.TEXT,
        json.dumps({"act": "login", "data": {"res": 0}}),
    )
    accept_login = _FakeWsMessage(
        WSMsgType.TEXT,
        json.dumps({"act": "login", "data": {"res": 1}}),
    )
    report = _FakeWsMessage(
        WSMsgType.TEXT,
        json.dumps({"act": "report", "data": {"data": "ignored"}}),
    )

    ws1 = _FakeWebSocket([reject_login])
    ws2 = _FakeWebSocket([accept_login, report])

    client = _ClientWithStubLogin(
        _FakeSession([ws1, ws2]),
        account="user@example.com",
        password="pw",
    )
    client._token = "stale-token"

    monkeypatch.setattr(api, "decode_report", lambda _packet: object())

    async def _collect_one_event():
        async for event in client.async_telemetry("device-1"):
            return event
        return None

    event = asyncio.run(_collect_one_event())

    assert isinstance(event, models.WatchdogTelemetryEvent)
    assert event.decode_error is False
    assert event.telemetry is not None
    assert client.login_calls == 1
    assert client.authenticated is True
    assert client._token == "fresh-token-1"

    # First websocket login attempted with stale token, second with refreshed token.
    assert ws1.sent[0]["act"] == "login"
    assert ws1.sent[0]["data"] == {"token": "stale-token"}
    assert ws2.sent[0]["act"] == "login"
    assert ws2.sent[0]["data"] == {"token": "fresh-token-1"}
