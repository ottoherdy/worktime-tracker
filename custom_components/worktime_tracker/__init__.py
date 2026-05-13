"""Worktime Tracker custom integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SERVICE_SET_LUNCH,
    SERVICE_LOG_ARRIVAL,
    SERVICE_LOG_DEPARTURE,
    SERVICE_RESET_TODAY,
    SERVICE_EXPORT_HISTORY,
    SERVICE_EDIT_DAY,
    SERVICE_LOG_SICK_DAY,
    LUNCH_YES,
    LUNCH_NO,
    LUNCH_UNKNOWN,
)
from .coordinator import WorktimeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration (yaml not supported, only config entries)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Worktime Tracker from a config entry."""
    coordinator = WorktimeCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once globally)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_LUNCH):
        await _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: WorktimeCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

        # Remove services if no entries left
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_SET_LUNCH,
                SERVICE_LOG_ARRIVAL,
                SERVICE_LOG_DEPARTURE,
                SERVICE_RESET_TODAY,
                SERVICE_EXPORT_HISTORY,
                SERVICE_EDIT_DAY,
                SERVICE_LOG_SICK_DAY,
            ):
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _get_coordinators(hass: HomeAssistant) -> list[WorktimeCoordinator]:
    return list(hass.data.get(DOMAIN, {}).values())


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    async def handle_set_lunch(call: ServiceCall) -> None:
        had_lunch = call.data.get("had_lunch", True)
        for coord in _get_coordinators(hass):
            await coord.async_set_lunch(LUNCH_YES if had_lunch else LUNCH_NO)

    async def handle_log_arrival(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_register_arrival(manual=True)

    async def handle_log_departure(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_register_departure(manual=True)

    async def handle_reset_today(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_reset_today()

    async def handle_export_history(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_export_history()

    async def handle_edit_day(call: ServiceCall) -> None:
        from datetime import date as date_type
        raw_date = call.data.get("date")
        target = date_type.fromisoformat(raw_date) if raw_date else dt_util.now().date()
        for coord in _get_coordinators(hass):
            await coord.async_edit_day(
                target_date=target,
                arrival=call.data.get("arrival"),
                departure=call.data.get("departure"),
                lunch=call.data.get("lunch"),
            )

    set_lunch_schema = vol.Schema({vol.Optional("had_lunch", default=True): cv.boolean})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_LUNCH, handle_set_lunch, schema=set_lunch_schema
    )
    hass.services.async_register(DOMAIN, SERVICE_LOG_ARRIVAL, handle_log_arrival)
    hass.services.async_register(DOMAIN, SERVICE_LOG_DEPARTURE, handle_log_departure)
    hass.services.async_register(DOMAIN, SERVICE_RESET_TODAY, handle_reset_today)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_HISTORY, handle_export_history)

    edit_day_schema = vol.Schema({
        vol.Optional("date"): cv.string,
        vol.Optional("arrival"): cv.string,
        vol.Optional("departure"): cv.string,
        vol.Optional("lunch"): vol.In([LUNCH_YES, LUNCH_NO, LUNCH_UNKNOWN]),
    })
    hass.services.async_register(DOMAIN, SERVICE_EDIT_DAY, handle_edit_day, schema=edit_day_schema)

    async def handle_log_sick_day(call: ServiceCall) -> None:
        from datetime import date as date_type
        raw_date = call.data.get("date") or None  # treat empty string as None
        target = date_type.fromisoformat(raw_date) if raw_date else dt_util.now().date()
        raw_hours = call.data.get("hours")
        hours = float(raw_hours) if raw_hours not in (None, "") else None
        for coord in _get_coordinators(hass):
            await coord.async_log_sick_day(target_date=target, hours=hours)

    sick_day_schema = vol.Schema({
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("hours"): vol.Any(None, vol.Coerce(float)),
    })
    hass.services.async_register(DOMAIN, SERVICE_LOG_SICK_DAY, handle_log_sick_day, schema=sick_day_schema)
