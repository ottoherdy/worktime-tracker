"""Binary sensors for Worktime Tracker."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATUS_AT_WORK, STATUS_DONE, STATUS_OVERTIME
from .coordinator import WorktimeCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WorktimeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AtWorkBinarySensor(coordinator, entry),
            DayCompleteBinarySensor(coordinator, entry),
        ]
    )


class _BaseBin(CoordinatorEntity[WorktimeCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _key: str = ""

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Worktime Tracker",
            manufacturer="Otto",
            model="Worktime Tracker",
        )


class AtWorkBinarySensor(_BaseBin):
    _key = "at_work"
    _attr_name = "At work"
    _attr_translation_key = "at_work"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool:
        status = self.coordinator.status()
        return status in (STATUS_AT_WORK, STATUS_OVERTIME)


class DayCompleteBinarySensor(_BaseBin):
    _key = "day_complete"
    _attr_name = "Day complete"
    _attr_translation_key = "day_complete"
    _attr_icon = "mdi:check-circle"

    @property
    def is_on(self) -> bool:
        return self.coordinator.status() == STATUS_DONE
