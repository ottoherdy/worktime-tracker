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
    SERVICE_EXPORT_ALL,
    SERVICE_EDIT_DAY,
    SERVICE_CLEAR_DAY,
    SERVICE_SET_PERIOD,
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
                SERVICE_EXPORT_ALL,
                SERVICE_EDIT_DAY,
                SERVICE_CLEAR_DAY,
                SERVICE_SET_PERIOD,
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
    """Return the coordinator(s) a service call should target.

    - With entry_prefix set: return the single entry whose instance_name
      slug matches (returns [] on miss).
    - Without entry_prefix: return ALL entries on single-instance setups
      (so legacy automations keep working), but only the oldest entry on
      multi-instance setups. Otherwise a card on the second instance with
      its entity_prefix slot empty would silently edit the first
      instance's day too.
    """
    active = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and isinstance(
            entry.runtime_data, WorktimeCoordinator
        ):
            active.append(entry)
    if not active:
        return []
    if entry_prefix:
        for entry in active:
            name = entry.data.get("instance_name") or entry.title or ""
            slug = "".join(c if c.isalnum() else "_" for c in name.lower())
            if slug == entry_prefix:
                return [entry.runtime_data]
        return []
    if len(active) == 1:
        return [active[0].runtime_data]
    # Multi-instance + no prefix → target the oldest only. async_entries
    # returns entries in creation order, so [0] is the original instance.
    _LOGGER.warning(
        "Worktime: service call without entry_prefix on a multi-instance "
        "setup — defaulting to the oldest entry (%s). Set entity_prefix "
        "on the other instance's card to address it specifically.",
        active[0].data.get("instance_name") or active[0].title,
    )
    return [active[0].runtime_data]


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

    async def handle_export_all(call: ServiceCall) -> None:
        from datetime import date as date_type
        raw_since = call.data.get("since") or None
        since = date_type.fromisoformat(raw_since) if raw_since else None
        force = bool(call.data.get("force", False))
        for coord in _get_coordinators(hass, _prefix(call)):
            await coord.async_export_all(since=since, force=force)

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

        prefix = _prefix(call)
        coords = _get_coordinators(hass, prefix)
        if not coords:
            _LOGGER.warning(
                "Worktime: edit_day for %s (prefix=%r) matched no instance — "
                "check the card's entity_prefix matches the config entry's "
                "instance_name slug. Active slugs: %s",
                target, prefix,
                [
                    "".join(
                        c if c.isalnum() else "_"
                        for c in (e.data.get("instance_name") or e.title or "").lower()
                    )
                    for e in hass.config_entries.async_entries(DOMAIN)
                    if hasattr(e, "runtime_data")
                ],
            )
            return
        _LOGGER.info(
            "Worktime: edit_day prefix=%r target=%s type=%s hours=%s "
            "arrival=%s departure=%s lunch=%s → %d coordinator(s)",
            prefix, target, day_type, hours, arrival, departure, lunch, len(coords),
        )

        for coord in coords:
            if day_type in ("sick", "off", "flex", "home"):
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

    async def handle_set_period(call: ServiceCall) -> None:
        from datetime import date as date_type, timedelta
        raw_start = call.data.get("start_date") or None
        raw_end = call.data.get("end_date") or None
        if not raw_start or not raw_end:
            _LOGGER.warning(
                "Worktime: set_period requires start_date and end_date"
            )
            return
        try:
            start = date_type.fromisoformat(raw_start)
            end = date_type.fromisoformat(raw_end)
        except ValueError:
            _LOGGER.warning(
                "Worktime: set_period got invalid dates start=%r end=%r",
                raw_start, raw_end,
            )
            return
        if end < start:
            _LOGGER.warning(
                "Worktime: set_period end_date %s is before start_date %s",
                end, start,
            )
            return

        day_type = call.data.get("type")
        raw_hours = call.data.get("hours")
        hours = float(raw_hours) if raw_hours not in (None, "") else None
        skip_existing = bool(call.data.get("skip_existing", False))

        prefix = _prefix(call)
        coords = _get_coordinators(hass, prefix)
        if not coords:
            _LOGGER.warning(
                "Worktime: set_period %s..%s (prefix=%r) matched no instance",
                start, end, prefix,
            )
            return

        span = (end - start).days + 1
        _LOGGER.info(
            "Worktime: set_period prefix=%r %s..%s (%d days) type=%s hours=%s "
            "skip_existing=%s → %d coordinator(s)",
            prefix, start, end, span, day_type, hours, skip_existing, len(coords),
        )

        for coord in coords:
            existing_dates = {
                e.get("date") for e in coord.history
            } | {
                e.get("date") for e in coord.leave_records
            }
            written = 0
            skipped = 0
            cur = start
            while cur <= end:
                iso = cur.isoformat()
                if skip_existing and iso in existing_dates:
                    skipped += 1
                else:
                    await coord.async_edit_day(
                        target_date=cur,
                        day_type=day_type,
                        hours=hours,
                    )
                    written += 1
                cur += timedelta(days=1)
            _LOGGER.info(
                "Worktime: set_period wrote %d, skipped %d existing for "
                "%s..%s (type=%s)",
                written, skipped, start, end, day_type,
            )

    async def handle_clear_day(call: ServiceCall) -> None:
        from datetime import date as date_type
        raw_date = call.data.get("date") or None
        target = date_type.fromisoformat(raw_date) if raw_date else dt_util.now().date()

        prefix = _prefix(call)
        coords = _get_coordinators(hass, prefix)
        if not coords:
            _LOGGER.warning(
                "Worktime: clear_day for %s (prefix=%r) matched no instance",
                target, prefix,
            )
            return
        for coord in coords:
            await coord.async_clear_day(target_date=target)

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

    export_all_schema = vol.Schema({
        vol.Optional("since"): vol.Any(None, cv.string),
        vol.Optional("force", default=False): cv.boolean,
        vol.Optional("entry_prefix"): cv.string,
    })
    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT_ALL, handle_export_all, schema=export_all_schema
    )

    edit_day_schema = vol.Schema({
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("arrival"): vol.Any(None, cv.string),
        vol.Optional("departure"): vol.Any(None, cv.string),
        vol.Optional("lunch"): vol.Any(None, "", vol.In([LUNCH_YES, LUNCH_NO, LUNCH_UNKNOWN])),
        vol.Optional("type"): vol.Any(None, "", vol.In(["normal", "sick", "off", "flex", "home"])),
        vol.Optional("hours"): vol.Any(None, "", vol.Coerce(float)),
        vol.Optional("entry_prefix"): cv.string,
    })
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_DAY, handle_edit_day, schema=edit_day_schema
    )

    clear_day_schema = vol.Schema({
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("entry_prefix"): cv.string,
    })
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_DAY, handle_clear_day, schema=clear_day_schema
    )

    set_period_schema = vol.Schema({
        vol.Required("start_date"): cv.string,
        vol.Required("end_date"): cv.string,
        vol.Required("type"): vol.In(["normal", "sick", "off", "flex", "home"]),
        vol.Optional("hours"): vol.Any(None, "", vol.Coerce(float)),
        vol.Optional("skip_existing", default=False): cv.boolean,
        vol.Optional("entry_prefix"): cv.string,
    })
    hass.services.async_register(
        DOMAIN, SERVICE_SET_PERIOD, handle_set_period, schema=set_period_schema
    )
