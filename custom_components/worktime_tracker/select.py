"""Select entities for Worktime Tracker edit-day form."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LUNCH_NO, LUNCH_UNKNOWN, LUNCH_YES


def _device_edit(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_edit")},
        name="Edit Day",
        manufacturer="Worktime Tracker",
        model="Edit helpers",
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([EditLunchSelect(entry)])


class EditLunchSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Edit lunch"
    _attr_icon = "mdi:food"
    _attr_options = [LUNCH_YES, LUNCH_NO, LUNCH_UNKNOWN]

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_edit_lunch"
        self._attr_device_info = _device_edit(entry)
        self._current = LUNCH_UNKNOWN

    @property
    def current_option(self) -> str:
        return self._current

    async def async_select_option(self, option: str) -> None:
        self._current = option
        self.async_write_ha_state()
