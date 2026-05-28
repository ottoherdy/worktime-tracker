"""Worktime Tracker custom integration."""
from __future__ import annotations

import json
import logging
import os
import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
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

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Path to the bundled Lovelace card JS
_WWW_DIR = os.path.join(os.path.dirname(__file__), "www")
_CARD_FILENAME = "worktime-tracker-card.js"


def _integration_version() -> str:
    """Read the version from manifest.json (best effort)."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "manifest.json")) as f:
            return str(json.load(f).get("version", "0"))
    except Exception:  # noqa: BLE001 — never block setup over a version string
        return "0"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static www path and auto-load the Lovelace card."""
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/{DOMAIN}_www",
            _WWW_DIR,
            cache_headers=False,
        )
    ])
    # Append the version as a cache-busting query param. The HA frontend
    # service worker and the browser cache the card JS aggressively keyed
    # by URL, so without this a HACS update keeps serving the old file and
    # the dashboard shows "Custom element doesn't exist" until a manual
    # cache clear. Changing the URL on every release forces a fresh fetch.
    version = await hass.async_add_executor_job(_integration_version)
    add_extra_js_url(hass, f"/{DOMAIN}_www/{_CARD_FILENAME}?v={version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Worktime Tracker from a config entry."""
    coordinator = WorktimeCoordinator(hass, entry)
    await coordinator.async_initialize()

    # Store coordinator on entry.runtime_data (HA 2024.x+)
    entry.runtime_data = coordinator

    # Prune stale devices from older versions that registered multiple devices.
    # The only valid device has identifiers {(DOMAIN, entry.entry_id)}.
    reg = dr.async_get(hass)
    valid_id = (DOMAIN, entry.entry_id)
    for device in dr.async_entries_for_config_entry(reg, entry.entry_id):
        if not any(ident[0] == DOMAIN for ident in device.identifiers):
            continue
        if valid_id in device.identifiers:
            continue
        _LOGGER.info("Worktime: removing stale device %s (%s)", device.name, device.id)
        reg.async_remove_device(device.id)

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


def _get_coordinators(
    hass: HomeAssistant, entry_prefix: str | None = None
) -> list[WorktimeCoordinator]:
    """Return active coordinators. If entry_prefix is given, only the one
    whose instance_name slug matches that prefix is returned."""
    coordinators = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if not (hasattr(entry, "runtime_data") and isinstance(
            entry.runtime_data, WorktimeCoordinator
        )):
            continue
        if entry_prefix:
            name = entry.data.get("instance_name") or entry.title or ""
            slug = "".join(c if c.isalnum() else "_" for c in name.lower())
            if slug != entry_prefix:
                continue
        coordinators.append(entry.runtime_data)
    return coordinators


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    def _prefix(call: ServiceCall) -> str | None:
        v = call.data.get("entry_prefix")
        return v.strip() if isinstance(v, str) and v.strip() else None

    async def handle_set_lunch(call: ServiceCall) -> None:
        had_lunch = call.data.get("had_lunch", True)
        for coord in _get_coordinators(hass, _prefix(call)):
            await coord.async_set_lunch(LUNCH_YES if had_lunch else LUNCH_NO)

    async def handle_log_arrival(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass, _prefix(call)):
            await coord.async_register_arrival(manual=True)

    async def handle_log_departure(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass, _prefix(call)):
            await coord.async_register_departure(manual=True)

    async def handle_reset_today(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass, _prefix(call)):
            await coord.async_reset_today()

    async def handle_export_today(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass, _prefix(call)):
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

        for coord in _get_coordinators(hass, _prefix(call)):
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

    set_lunch_schema = vol.Schema({
        vol.Optional("had_lunch", default=True): cv.boolean,
        vol.Optional("entry_prefix"): cv.string,
    })
    no_arg_schema = vol.Schema({vol.Optional("entry_prefix"): cv.string})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_LUNCH, handle_set_lunch, schema=set_lunch_schema
    )
    hass.services.async_register(DOMAIN, SERVICE_LOG_ARRIVAL, handle_log_arrival, schema=no_arg_schema)
    hass.services.async_register(DOMAIN, SERVICE_LOG_DEPARTURE, handle_log_departure, schema=no_arg_schema)
    hass.services.async_register(DOMAIN, SERVICE_RESET_TODAY, handle_reset_today, schema=no_arg_schema)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_TODAY, handle_export_today, schema=no_arg_schema)

    edit_day_schema = vol.Schema({
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("arrival"): vol.Any(None, cv.string),
        vol.Optional("departure"): vol.Any(None, cv.string),
        vol.Optional("lunch"): vol.Any(None, "", vol.In([LUNCH_YES, LUNCH_NO, LUNCH_UNKNOWN])),
        vol.Optional("type"): vol.Any(None, "", vol.In(["normal", "sick", "off", "flex"])),
        vol.Optional("hours"): vol.Any(None, "", vol.Coerce(float)),
        vol.Optional("entry_prefix"): cv.string,
    })
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_DAY, handle_edit_day, schema=edit_day_schema
    )
