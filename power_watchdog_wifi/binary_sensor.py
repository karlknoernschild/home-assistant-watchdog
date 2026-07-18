"""Binary sensors for Power Watchdog WiFi."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WatchdogConfigEntry
from .entity import WatchdogEntity
from .models import WatchdogSnapshot, WatchdogTelemetry


@dataclass(frozen=True, kw_only=True)
class WatchdogBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Watchdog binary sensor."""

    value_fn: Callable[[WatchdogTelemetry], bool]


BINARY_SENSORS: tuple[WatchdogBinarySensorDescription, ...] = (
    WatchdogBinarySensorDescription(
        key="l1_error_present",
        translation_key="l1_error_present",
        value_fn=lambda data: data.leg1.error_raw != 0,
    ),
    WatchdogBinarySensorDescription(
        key="l2_error_present",
        translation_key="l2_error_present",
        value_fn=lambda data: data.leg2.error_raw != 0,
    ),
    WatchdogBinarySensorDescription(
        key="error_present",
        translation_key="error_present",
        value_fn=lambda data: data.leg1.error_raw != 0 or data.leg2.error_raw != 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Power Watchdog binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        WatchdogBinarySensor(entry, coordinator, description)
        for description in BINARY_SENSORS
    )


class WatchdogBinarySensor(WatchdogEntity, BinarySensorEntity):
    """A Power Watchdog binary sensor."""

    entity_description: WatchdogBinarySensorDescription

    def __init__(
        self,
        entry: WatchdogConfigEntry,
        coordinator,
        description: WatchdogBinarySensorDescription,
    ) -> None:
        super().__init__(entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data['device_no']}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor value."""
        snapshot: WatchdogSnapshot = self.coordinator.data
        if snapshot.latest_telemetry is None:
            return None
        return self.entity_description.value_fn(snapshot.latest_telemetry)
