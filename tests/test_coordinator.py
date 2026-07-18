"""Coordinator transition tests with lightweight Home Assistant stubs."""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    core_mod = types.ModuleType("homeassistant.core")
    helpers_mod = types.ModuleType("homeassistant.helpers")
    storage_mod = types.ModuleType("homeassistant.helpers.storage")
    coordinator_mod = types.ModuleType("homeassistant.helpers.update_coordinator")
    util_mod = types.ModuleType("homeassistant.util")
    dt_mod = types.ModuleType("homeassistant.util.dt")

    class HomeAssistant:
        pass

    class Store:
        _memory: dict[str, dict] = {}

        def __init__(self, hass, version, key):
            self._key = key

        async def async_load(self):
            return self._memory.get(self._key)

        async def async_save(self, data):
            self._memory[self._key] = data

    class DataUpdateCoordinator:
        @classmethod
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, hass, logger, name):
            self.hass = hass
            self.data = None

        def async_set_updated_data(self, data):
            self.data = data

        def async_update_listeners(self):
            return None

        def async_set_update_error(self, err):
            self.last_error = err

    def utcnow():
        return datetime.now(UTC)

    def as_local(value):
        return value.astimezone()

    core_mod.HomeAssistant = HomeAssistant
    storage_mod.Store = Store
    coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    dt_mod.utcnow = utcnow
    dt_mod.as_local = as_local

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.helpers"] = helpers_mod
    sys.modules["homeassistant.helpers.storage"] = storage_mod
    sys.modules["homeassistant.helpers.update_coordinator"] = coordinator_mod
    sys.modules["homeassistant.util"] = util_mod
    sys.modules["homeassistant.util.dt"] = dt_mod


def _install_integration_stubs() -> None:
    api_mod = types.ModuleType("power_watchdog_wifi.api")

    class ReadOnlyWatchdogClient:
        pass

    class WatchdogAuthError(Exception):
        pass

    class WatchdogConnectionError(Exception):
        pass

    api_mod.ReadOnlyWatchdogClient = ReadOnlyWatchdogClient
    api_mod.WatchdogAuthError = WatchdogAuthError
    api_mod.WatchdogConnectionError = WatchdogConnectionError
    sys.modules["power_watchdog_wifi.api"] = api_mod

    repairs_mod = types.ModuleType("power_watchdog_wifi.repairs")
    repairs_mod.clear_runtime_issues = lambda hass, entry_id: None
    repairs_mod.create_auth_failed_issue = lambda hass, entry_id: None
    repairs_mod.create_cannot_connect_issue = lambda hass, entry_id: None
    sys.modules["power_watchdog_wifi.repairs"] = repairs_mod


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "power_watchdog_wifi"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT / PACKAGE_NAME)]  # type: ignore[attr-defined]
    sys.modules[PACKAGE_NAME] = package

_install_homeassistant_stubs()
_install_integration_stubs()

_load_module("power_watchdog_wifi.const", ROOT / "power_watchdog_wifi" / "const.py")
models = _load_module(
    "power_watchdog_wifi.models",
    ROOT / "power_watchdog_wifi" / "models.py",
)
coordinator_mod = _load_module(
    "power_watchdog_wifi.coordinator",
    ROOT / "power_watchdog_wifi" / "coordinator.py",
)


def _sample_telemetry(total_energy_seed: float) -> object:
    return models.WatchdogTelemetry(
        leg1=models.LegTelemetry(120.0, 1.0, 120.0, total_energy_seed, 60.0, 0, 0),
        leg2=models.LegTelemetry(120.0, 1.0, 120.0, total_energy_seed, 60.0, 0, 0),
    )


def test_listen_updates_reconnect_and_timeout_recovery() -> None:
    class FakeClient:
        def __init__(self):
            self.calls = 0

        async def async_list_devices(self):
            return [{"device_no": "dev1"}]

        async def async_telemetry(self, device_no):
            self.calls += 1
            if self.calls == 1:
                yield models.WatchdogTelemetryEvent(telemetry=_sample_telemetry(1.0))
                return
            if self.calls == 2:
                yield models.WatchdogTelemetryEvent(telemetry=_sample_telemetry(1.5))
                return
            raise asyncio.CancelledError

    coordinator = coordinator_mod.WatchdogCoordinator(
        hass=types.SimpleNamespace(),
        client=FakeClient(),
        device_no="dev1",
        initial_device_metadata=None,
    )
    coordinator.config_entry = types.SimpleNamespace(entry_id="entry-1")
    coordinator._timed_out = True

    async def _run():
        try:
            await coordinator._async_listen()
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())

    assert coordinator.data.packet_count == 2
    assert coordinator.data.reconnect_count == 1
    assert coordinator._timed_out is False


def test_timeout_tracker_marks_coordinator_unavailable() -> None:
    coordinator = coordinator_mod.WatchdogCoordinator(
        hass=types.SimpleNamespace(),
        client=types.SimpleNamespace(async_list_devices=lambda: []),
        device_no="dev1",
        initial_device_metadata=None,
    )
    coordinator.config_entry = types.SimpleNamespace(entry_id="entry-1")
    coordinator.data = replace(
        coordinator.data,
        latest_telemetry=_sample_telemetry(2.0),
        last_telemetry_timestamp=datetime.now(UTC) - timedelta(hours=1),
    )

    sleep_calls = {"count": 0}
    original_sleep = coordinator_mod.asyncio.sleep

    async def fake_sleep(_seconds):
        sleep_calls["count"] += 1
        if sleep_calls["count"] > 1:
            raise asyncio.CancelledError

    coordinator_mod.asyncio.sleep = fake_sleep
    try:
        asyncio.run(coordinator._async_track_availability_timeout())
    except asyncio.CancelledError:
        pass
    finally:
        coordinator_mod.asyncio.sleep = original_sleep

    assert coordinator._timed_out is True
    assert coordinator.available is False
