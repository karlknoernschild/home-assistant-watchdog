"""Shared pytest harness configuration for this integration."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CUSTOM_COMPONENTS = ROOT / "custom_components"
if str(CUSTOM_COMPONENTS) not in sys.path:
    sys.path.insert(0, str(CUSTOM_COMPONENTS))


@pytest.fixture(autouse=True)
def _block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent accidental outbound network access during tests."""
    original_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address):  # type: ignore[no-untyped-def]
        if isinstance(address, tuple):
            host = address[0]
            if host in {"127.0.0.1", "::1", "localhost"}:
                return original_connect(self, address)
            raise AssertionError(f"External network access blocked in tests: {host}")
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
