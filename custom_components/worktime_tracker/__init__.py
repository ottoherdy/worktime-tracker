"""Worktime Tracker custom integration."""
from __future__ import annotations

import logging
import os
import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
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
    SERVICE_EXPORT_TODAY,
    SERVICE_EDIT_DAY,
    LUNCH_YES,
    LUNCH_NO,
    LUNCH_UNKNOWN,
)
from .coordinator import WorktimeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Path to the bundled Lovelace card JS
_WWW_DIR = os.path.join(os.path.dirname(__file__), "www")
_CARD_FILENAME = "worktime-tracker-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static www path so the Lovelace card JS is served."""
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/{DOMAIN}_www",
            _WWW_DIR,
            cache_headers=False,
        )
    ])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Worktime Tracker from a config entry."""
    coordinator = WorktimeCoordinator(hass, entry)
    await coordinator.async_initialize()

    # Store coordinator on entry.runtime_data (HA 2024.x+)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services only once globally
    if not hass.services.has_service(DOMAIN, SERVICE_SET_LUNCH):
        await _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: WorktimeCoordinator = entry.runtime_data
        await coordinator.async_shutdown()

        # Remove services if no entries left
        remaining = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.state.recoverable
        ]
        if not remaining:
            for service in (
                SERVICE_SET_LUNCH,
                SERVICE_LOG_ARRIVAL,
                SERVICE_LOG_DEPARTURE,
                SERVICE_RESET_TODAY,
                SERVICE_EXPORT_TODAY,
                SERVICE_EDIT_DAY,
            ):
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _get_coordinators(hass: HomeAssistant) -> list[WorktimeCoordinator]:
    """Return all active coordinators from runtime_data."""
    coordinators = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and isinstance(
            entry.runtime_data, WorktimeCoordinator
        ):
            coordinators.append(entry.runtime_data)
    return coordinators


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

    async def handle_export_today(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_export_today()

    async def handle_edit_day(call: ServiceCall) -> None:
        from datetime import date as date_type
        raw_date = call.data.get("date") or None
        target = date_type.fromisoformat(raw_date) if raw_date else dt_util.now().date()
        day_type = call.data.get("type") or None
        raw_hours = call.data.get("hours")
        hours = float(raw_hours) if raw_hours not in (None, "") else None
        arrival = call.data.get("arrival") or None
        departure = call.data.get("departure") or None
        lunch = call.data.get("lunch") or None

        for coord in _get_coordinators(hass):
            if day_type in ("sick", "off"):
                await coord.async_edit_day(
                    target_date=target,
                    day_type=day_type,
                    hours=hours,
                )
            else:
                await coord.async_edit_day(
                    target_date=target,
                    arrival=arrival,
                    departure=departure,
                    lunch=lunch,
                    day_type=day_type,
                    hours=hours,
                )

    set_lunch_schema = vol.Schema({vol.Optional("had_lunch", default=True): cv.boolean})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_LUNCH, handle_set_lunch, schema=set_lunch_schema
    )
    hass.services.async_register(DOMAIN, SERVICE_LOG_ARRIVAL, handle_log_arrival)
    hass.services.async_register(DOMAIN, SERVICE_LOG_DEPARTURE, handle_log_departure)
    hass.services.async_register(DOMAIN, SERVICE_RESET_TODAY, handle_reset_today)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_TODAY, handle_export_today)

    edit_day_schema = vol.Schema({
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("arrival"): vol.Any(None, cv.string),
        vol.Optional("departure"): vol.Any(None, cv.string),
        vol.Optional("lunch"): vol.Any(None, "", vol.In([LUNCH_YES, LUNCH_NO, LUNCH_UNKNOWN])),
        vol.Optional("type"): vol.Any(None, "", vol.In(["normal", "sick", "off"])),
        vol.Optional("hours"): vol.Any(None, "", vol.Coerce(float)),
    })
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_DAY, handle_edit_day, schema=edit_day_schema
    )
