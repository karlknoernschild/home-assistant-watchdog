"""Base entity for Power Watchdog WiFi."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatchdogConfigEntry
from .const import (
    CONF_CONNECT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_NO,
    CONF_FIRMWARE,
    CONF_MCU_FIRMWARE,
    CONF_SOCKET_STATE,
    CONF_START_FROM,
    DOMAIN,
)
from .coordinator import WatchdogCoordinator
from .models import WatchdogDeviceMetadata


class WatchdogEntity(CoordinatorEntity[WatchdogCoordinator]):
    """Base Power Watchdog entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: WatchdogConfigEntry,
        coordinator: WatchdogCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._device_no = entry.data[CONF_DEVICE_NO]

    @property
    def _metadata(self) -> WatchdogDeviceMetadata:
        """Return refreshed metadata with config-entry fallback values."""
        # Prefer coordinator metadata because it is refreshed during runtime;
        # config-entry data is only a persisted fallback.
        snapshot_metadata = self.coordinator.data.device_metadata
        if snapshot_metadata is not None:
            return snapshot_metadata

        return WatchdogDeviceMetadata(
            device_no=self._device_no,
            device_id=self._entry.data.get(CONF_DEVICE_ID),
            name=self._entry.data.get(CONF_DEVICE_NAME),
            firmware=self._entry.data.get(CONF_FIRMWARE),
            mcu_firmware=self._entry.data.get(CONF_MCU_FIRMWARE),
            connect_type=self._entry.data.get(CONF_CONNECT_TYPE),
            socket_state=self._entry.data.get(CONF_SOCKET_STATE),
            start_from=self._entry.data.get(CONF_START_FROM),
            cloud_identifiers=tuple(
                value
                for value in (
                    self._entry.data.get(CONF_DEVICE_ID),
                    self._device_no,
                )
                if value is not None
            ),
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return dynamic device registry information."""
        metadata = self._metadata
        identifiers = {(DOMAIN, self._device_no)}
        if metadata.device_id:
            identifiers.add((DOMAIN, metadata.device_id))
        return DeviceInfo(
            identifiers=identifiers,
            name=metadata.name or self._entry.data[CONF_DEVICE_NAME],
            manufacturer="Hughes Autoformers",
            model="Power Watchdog WiFi",
            serial_number=self._device_no,
            sw_version=metadata.firmware,
            hw_version=metadata.mcu_firmware,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return normalized cloud metadata attributes."""
        metadata = self._metadata
        attrs = {
            "connect_type": metadata.connect_type,
            "socket_state": metadata.socket_state,
            "start_from": metadata.start_from,
        }
        normalized = {key: value for key, value in attrs.items() if value is not None}
        if not normalized:
            return None
        return normalized

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self.coordinator.available
