"""Sensors for Power Watchdog WiFi."""

from __future__ import annotations

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
from .models import WatchdogSnapshot, WatchdogTelemetry


@dataclass(frozen=True, kw_only=True)
class WatchdogSensorDescription(SensorEntityDescription):
    """Describe a Watchdog sensor."""

    value_fn: Callable[[WatchdogTelemetry], float]


SENSORS: tuple[WatchdogSensorDescription, ...] = (
    WatchdogSensorDescription(
        key="l1_voltage",
        translation_key="l1_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.leg1.voltage_v,
    ),
    WatchdogSensorDescription(
        key="l2_voltage",
        translation_key="l2_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.leg2.voltage_v,
    ),
    WatchdogSensorDescription(
        key="l1_current",
        translation_key="l1_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.leg1.current_a,
    ),
    WatchdogSensorDescription(
        key="l2_current",
        translation_key="l2_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.leg2.current_a,
    ),
    WatchdogSensorDescription(
        key="total_current",
        translation_key="total_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.total_current_a,
    ),
    WatchdogSensorDescription(
        key="l1_power",
        translation_key="l1_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.leg1.power_w,
    ),
    WatchdogSensorDescription(
        key="l2_power",
        translation_key="l2_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.leg2.power_w,
    ),
    WatchdogSensorDescription(
        key="total_power",
        translation_key="total_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.total_power_w,
    ),
    WatchdogSensorDescription(
        key="l1_energy",
        translation_key="l1_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.leg1.energy_kwh,
    ),
    WatchdogSensorDescription(
        key="l2_energy",
        translation_key="l2_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.leg2.energy_kwh,
    ),
    WatchdogSensorDescription(
        key="total_energy",
        translation_key="total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.total_energy_kwh,
    ),
    WatchdogSensorDescription(
        key="frequency",
        translation_key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.frequency_hz,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WatchdogConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Power Watchdog sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        WatchdogSensor(entry, coordinator, description)
        for description in SENSORS
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
        if snapshot.latest_telemetry is None:
            return None
        return self.entity_description.value_fn(snapshot.latest_telemetry)
