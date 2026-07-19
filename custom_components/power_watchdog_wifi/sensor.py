"""Sensors for Power Watchdog WiFi."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WatchdogConfigEntry
from .entity import WatchdogEntity
from .models import WatchdogSnapshot

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WatchdogSensorDescription(SensorEntityDescription):
    """Describe a Watchdog sensor."""

    value_fn: Callable[[WatchdogSnapshot], float | None]


SENSORS: tuple[WatchdogSensorDescription, ...] = (
    # Baseline live telemetry sensors (mapped directly from decoded packets).
    WatchdogSensorDescription(
        key="l1_voltage",
        translation_key="l1_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg1.voltage_v
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l2_voltage",
        translation_key="l2_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg2.voltage_v
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l1_current",
        translation_key="l1_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg1.current_a
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l2_current",
        translation_key="l2_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg2.current_a
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="total_current",
        translation_key="total_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.total_current_a
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l1_power",
        translation_key="l1_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg1.power_w
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l2_power",
        translation_key="l2_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg2.power_w
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="total_power",
        translation_key="total_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.total_power_w
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l1_energy",
        translation_key="l1_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg1.energy_kwh
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="l2_energy",
        translation_key="l2_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.leg2.energy_kwh
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="total_energy",
        translation_key="total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.total_energy_kwh
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    WatchdogSensorDescription(
        key="frequency",
        translation_key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda snapshot: (
            snapshot.latest_telemetry.frequency_hz
            if snapshot.latest_telemetry is not None
            else None
        ),
    ),
    # Derived metrics intentionally labeled as "derived_*" to distinguish them
    # from native device fields.
    WatchdogSensorDescription(
        key="derived_rolling_average_power",
        translation_key="derived_rolling_average_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snapshot: snapshot.derived_rolling_average_power_w,
    ),
    WatchdogSensorDescription(
        key="derived_today_energy",
        translation_key="derived_today_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda snapshot: snapshot.derived_today_energy_kwh,
    ),
    WatchdogSensorDescription(
        key="derived_yesterday_energy",
        translation_key="derived_yesterday_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda snapshot: snapshot.derived_yesterday_energy_kwh,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Power Watchdog sensors."""
    coordinator = entry.runtime_data.coordinator
    _LOGGER.debug(
        "Setting up %s sensor entities for device_no=%s",
        len(SENSORS),
        coordinator.device_no,
    )
    async_add_entities(
        WatchdogSensor(entry, coordinator, description) for description in SENSORS
    )


class WatchdogSensor(WatchdogEntity, SensorEntity):
    """A Power Watchdog sensor."""

    entity_description: WatchdogSensorDescription

    def __init__(
        self,
        entry: WatchdogConfigEntry,
        coordinator,
        description: WatchdogSensorDescription,
    ) -> None:
        super().__init__(entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data['device_no']}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        snapshot: WatchdogSnapshot = self.coordinator.data
        return self.entity_description.value_fn(snapshot)
