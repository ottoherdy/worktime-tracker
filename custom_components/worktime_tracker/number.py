"""Number entities for Worktime Tracker — arrival/departure margins."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_MARGIN_MINUTES
from .coordinator import WorktimeCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WorktimeCoordinator = entry.runtime_data
    async_add_entities(
        [
            ArrivalMarginNumber(coordinator, entry),
            DepartureMarginNumber(coordinator, entry),
        ]
    )


class _MarginNumberBase(CoordinatorEntity[WorktimeCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = float(MAX_MARGIN_MINUTES)
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        name = (entry.data.get("instance_name") or entry.title or "Worktime Tracker").strip()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Worktime Tracker",
            model="Work Time Tracking",
        )


class ArrivalMarginNumber(_MarginNumberBase):
    _attr_name = "Arrival margin"
    _attr_icon = "mdi:clock-plus-outline"
    _attr_translation_key = "arrival_margin"

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_arrival_margin"

    @property
    def native_value(self) -> float:
        return float(self.coordinator.arrival_margin_minutes)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_arrival_margin_minutes(int(value))


class DepartureMarginNumber(_MarginNumberBase):
    _attr_name = "Departure margin"
    _attr_icon = "mdi:clock-minus-outline"
    _attr_translation_key = "departure_margin"

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_departure_margin"

    @property
    def native_value(self) -> float:
        return float(self.coordinator.departure_margin_minutes)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_departure_margin_minutes(int(value))
