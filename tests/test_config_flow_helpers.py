"""Config flow helper tests."""

from __future__ import annotations

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
    package.__path__ = [str(ROOT / PACKAGE_NAME)]  # type: ignore[attr-defined]
    sys.modules[PACKAGE_NAME] = package

helpers = _load_module(
    "power_watchdog_wifi.config_flow_helpers",
    ROOT / "power_watchdog_wifi" / "config_flow_helpers.py",
)


def test_build_device_options_uses_device_name_fallback() -> None:
    devices = [
        {"device_no": "111", "name": "Main RV"},
        {"device_no": "222"},
    ]
    assert helpers.build_device_options(devices) == {"111": "Main RV", "222": "222"}


def test_find_device_by_device_no_returns_selected_device() -> None:
    devices = [{"device_no": "111"}, {"device_no": "222"}]
    assert helpers.find_device_by_device_no(devices, "222") == {"device_no": "222"}
