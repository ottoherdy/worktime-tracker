"""Text entities for Worktime Tracker edit-day form."""
from __future__ import annotations

import re

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN


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
    async_add_entities([
        EditDateText(entry),
        EditArrivalText(entry),
        EditDepartureText(entry),
    ])


class _EditText(TextEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _key: str = ""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_device_info = _device_edit(entry)
        self._value: str = ""

    @property
    def native_value(self) -> str:
        return self._value

    async def async_set_value(self, value: str) -> None:
        self._value = value
        self.async_write_ha_state()


class EditDateText(_EditText):
    _key = "edit_date"
    _attr_name = "Edit date"
    _attr_icon = "mdi:calendar-edit"
    _attr_native_min = 0
    _attr_native_max = 10
    _attr_pattern = r"\d{4}-\d{2}-\d{2}|"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._value = dt_util.now().date().isoformat()


class EditArrivalText(_EditText):
    _key = "edit_arrival"
    _attr_name = "Edit arrival"
    _attr_icon = "mdi:login"
    _attr_native_min = 0
    _attr_native_max = 5
    _attr_pattern = r"\d{2}:\d{2}|"


class EditDepartureText(_EditText):
    _key = "edit_departure"
    _attr_name = "Edit departure"
    _attr_icon = "mdi:logout"
    _attr_native_min = 0
    _attr_native_max = 5
    _attr_pattern = r"\d{2}:\d{2}|"
