"""Base entity for Power Watchdog WiFi."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatchdogConfigEntry
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_NO,
    CONF_FIRMWARE,
    CONF_MCU_FIRMWARE,
    DOMAIN,
)
from .coordinator import WatchdogCoordinator


class WatchdogEntity(CoordinatorEntity[WatchdogCoordinator]):
    """Base Power Watchdog entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: WatchdogConfigEntry,
        coordinator: WatchdogCoordinator,
    ) -> None:
        super().__init__(coordinator)
        device_no = entry.data[CONF_DEVICE_NO]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_no)},
            name=entry.data[CONF_DEVICE_NAME],
            manufacturer="Hughes Autoformers",
            model="Power Watchdog WiFi",
            serial_number=device_no,
            sw_version=entry.data.get(CONF_FIRMWARE),
            hw_version=entry.data.get(CONF_MCU_FIRMWARE),
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self.coordinator.available
