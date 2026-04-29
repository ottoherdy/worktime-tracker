"""Switch entities for Worktime Tracker."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WorktimeCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WorktimeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutoDepartureSwitch(coordinator, entry)])


class AutoDepartureSwitch(CoordinatorEntity[WorktimeCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto departure"
    _attr_icon = "mdi:clock-out"

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_auto_departure"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_today")},
            name="Today",
            manufacturer="Worktime Tracker",
            model="Daily tracking",
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.auto_departure_enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_departure_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_departure_enabled(False)
