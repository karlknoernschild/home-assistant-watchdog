"""Diagnostics redaction tests."""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
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
    components = types.ModuleType("homeassistant.components")
    diagnostics_mod = types.ModuleType("homeassistant.components.diagnostics")
    core_mod = types.ModuleType("homeassistant.core")
    helpers_mod = types.ModuleType("homeassistant.helpers")
    device_registry_mod = types.ModuleType("homeassistant.helpers.device_registry")

    def async_redact_data(data, redact_keys):
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if key in redact_keys:
                    redacted[key] = "**REDACTED**"
                else:
                    redacted[key] = async_redact_data(value, redact_keys)
            return redacted
        if isinstance(data, list):
            return [async_redact_data(value, redact_keys) for value in data]
        if isinstance(data, tuple):
            return [async_redact_data(value, redact_keys) for value in data]
        return data

    class HomeAssistant:
        pass

    @dataclass
    class DeviceEntry:
        id: str
        identifiers: set[tuple[str, str]]

    diagnostics_mod.async_redact_data = async_redact_data
    core_mod.HomeAssistant = HomeAssistant
    device_registry_mod.DeviceEntry = DeviceEntry

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.diagnostics"] = diagnostics_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.helpers"] = helpers_mod
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_mod


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "power_watchdog_wifi"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [  # type: ignore[attr-defined]
        str(ROOT / "custom_components" / PACKAGE_NAME)
    ]
    sys.modules[PACKAGE_NAME] = package
sys.modules[PACKAGE_NAME].WatchdogConfigEntry = object

_install_homeassistant_stubs()

models = _load_module(
    "power_watchdog_wifi.models",
    ROOT / "custom_components" / "power_watchdog_wifi" / "models.py",
)
_load_module(
    "power_watchdog_wifi.const",
    ROOT / "custom_components" / "power_watchdog_wifi" / "const.py",
)
_load_module(
    "power_watchdog_wifi.protocol",
    ROOT / "custom_components" / "power_watchdog_wifi" / "protocol.py",
)
diagnostics = _load_module(
    "power_watchdog_wifi.diagnostics",
    ROOT / "custom_components" / "power_watchdog_wifi" / "diagnostics.py",
)


def test_config_entry_diagnostics_redacts_sensitive_fields() -> None:
    snapshot = models.WatchdogSnapshot(
        device_metadata=models.WatchdogDeviceMetadata(
            device_no="device-no",
            device_id="internal-id",
            cloud_identifiers=("id1", "id2"),
        )
    )
    runtime_data = types.SimpleNamespace(
        coordinator=types.SimpleNamespace(data=snapshot),
        client=types.SimpleNamespace(authenticated=True),
    )
    entry = types.SimpleNamespace(
        entry_id="entry-1",
        title="Watchdog",
        data={
            "account": "user@example.com",
            "password": "secret",
            "device_no": "device-no",
            "device_id": "internal-id",
        },
        options={},
        runtime_data=runtime_data,
    )

    payload = asyncio.run(diagnostics.async_get_config_entry_diagnostics(None, entry))
    assert payload["config_entry"]["data"]["account"] == "**REDACTED**"
    assert payload["config_entry"]["data"]["password"] == "**REDACTED**"
    assert payload["config_entry"]["data"]["device_no"] == "**REDACTED**"
    assert payload["runtime"]["snapshot"]["device_metadata"]["cloud_identifiers"] == (
        "**REDACTED**"
    )
