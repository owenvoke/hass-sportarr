"""Sensors for Sportarr."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SportarrConfigEntry, SportarrData
from .entity import SportarrEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SportarrSensorEntityDescription(SensorEntityDescription):
    """Describes a Sportarr sensor."""

    value_fn: Callable[[SportarrData], int]


SENSORS: tuple[SportarrSensorEntityDescription, ...] = (
    SportarrSensorEntityDescription(
        key="queue",
        translation_key="queue",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.queue,
    ),
    SportarrSensorEntityDescription(
        key="pending_imports",
        translation_key="pending_imports",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pending_imports,
    ),
    SportarrSensorEntityDescription(
        key="missing",
        translation_key="missing",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.missing,
    ),
    SportarrSensorEntityDescription(
        key="cutoff_unmet",
        translation_key="cutoff_unmet",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.cutoff_unmet,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SportarrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(
        SportarrSensor(entry.runtime_data, description, description.key)
        for description in SENSORS
    )


class SportarrSensor(SportarrEntity, SensorEntity):
    """A count of events or downloads."""

    entity_description: SportarrSensorEntityDescription

    @property
    def native_value(self) -> int:
        """Return the count."""
        return self.entity_description.value_fn(self.coordinator.data)
