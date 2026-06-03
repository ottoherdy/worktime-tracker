"""Config flow for Worktime Tracker."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_DEPARTURE_ENABLED,
    CONF_AUTO_DEPARTURE_TIME,
    CONF_AUTO_EXPORT_DELAY_HOURS,
    CONF_AUTO_EXPORT_ENABLED,
    CONF_AUTO_LUNCH_DEFAULT,
    CONF_FORGOT_DEPARTURE_ENABLED,
    CONF_FORGOT_DEPARTURE_OFFSET_MIN,
    CONF_ZONE_EXIT_GRACE_MIN,
    CONF_LUNCH_DEDUCTION,
    CONF_LUNCH_TIME,
    CONF_MORNING_REMINDER_ENABLED,
    CONF_MORNING_REMINDER_TIME,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON,
    CONF_SHEETS_ENTRY_ID,
    CONF_SHEETS_WORKSHEET,
    CONF_WEEKLY_TARGET,
    CONF_WORK_ZONE,
    CONF_WORKDAY_HOURS,
    DEFAULT_AUTO_DEPARTURE_ENABLED,
    DEFAULT_AUTO_DEPARTURE_TIME,
    DEFAULT_AUTO_EXPORT_DELAY_HOURS,
    DEFAULT_AUTO_EXPORT_ENABLED,
    DEFAULT_AUTO_LUNCH_DEFAULT,
    DEFAULT_FORGOT_DEPARTURE_ENABLED,
    DEFAULT_FORGOT_DEPARTURE_OFFSET_MIN,
    DEFAULT_ZONE_EXIT_GRACE_MIN,
    DEFAULT_LUNCH_DEDUCTION,
    DEFAULT_LUNCH_TIME,
    DEFAULT_MORNING_REMINDER_ENABLED,
    DEFAULT_MORNING_REMINDER_TIME,
    DEFAULT_SHEETS_WORKSHEET,
    DEFAULT_WEEKLY_TARGET,
    DEFAULT_WORKDAY_HOURS,
    DOMAIN,
)


def _notify_options(hass: HomeAssistant) -> list[selector.SelectOptionDict]:
    """Build a sorted dropdown list of available notify.* services.

    We store / pass the bare service name (without the `notify.` prefix)
    to stay backward-compatible with existing configs."""
    services = hass.services.async_services().get("notify", {})
    names = sorted(services.keys())
    return [
        selector.SelectOptionDict(value=name, label=f"notify.{name}")
        for name in names
    ]


def _build_user_schema(
    hass: HomeAssistant,
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    notify_opts = _notify_options(hass)
    return vol.Schema(
        {
            vol.Optional(
                "instance_name", default=defaults.get("instance_name", "Worktime Tracker")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_PERSON, default=defaults.get(CONF_PERSON)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["person", "device_tracker"])
            ),
            vol.Required(
                CONF_WORK_ZONE, default=defaults.get(CONF_WORK_ZONE)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="zone")
            ),
            vol.Optional(
                CONF_NOTIFY_SERVICE, default=defaults.get(CONF_NOTIFY_SERVICE, "")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_opts,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                    sort=True,
                )
            ),
            vol.Required(
                CONF_LUNCH_TIME, default=defaults.get(CONF_LUNCH_TIME, DEFAULT_LUNCH_TIME)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_WORKDAY_HOURS,
                default=defaults.get(CONF_WORKDAY_HOURS, DEFAULT_WORKDAY_HOURS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=24, step=0.25, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_LUNCH_DEDUCTION,
                default=defaults.get(CONF_LUNCH_DEDUCTION, DEFAULT_LUNCH_DEDUCTION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=4, step=0.25, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_WEEKLY_TARGET,
                default=defaults.get(CONF_WEEKLY_TARGET, DEFAULT_WEEKLY_TARGET),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=80, step=0.5, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Optional(
                CONF_SHEETS_ENTRY_ID, default=defaults.get(CONF_SHEETS_ENTRY_ID, "")
            ): selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="google_sheets")
            ),
            vol.Optional(
                CONF_SHEETS_WORKSHEET,
                default=defaults.get(CONF_SHEETS_WORKSHEET, DEFAULT_SHEETS_WORKSHEET),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_AUTO_LUNCH_DEFAULT,
                default=defaults.get(CONF_AUTO_LUNCH_DEFAULT, DEFAULT_AUTO_LUNCH_DEFAULT),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_AUTO_DEPARTURE_ENABLED,
                default=defaults.get(CONF_AUTO_DEPARTURE_ENABLED, DEFAULT_AUTO_DEPARTURE_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_AUTO_DEPARTURE_TIME,
                default=defaults.get(CONF_AUTO_DEPARTURE_TIME, DEFAULT_AUTO_DEPARTURE_TIME),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_AUTO_EXPORT_ENABLED,
                default=defaults.get(CONF_AUTO_EXPORT_ENABLED, DEFAULT_AUTO_EXPORT_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_AUTO_EXPORT_DELAY_HOURS,
                default=defaults.get(CONF_AUTO_EXPORT_DELAY_HOURS, DEFAULT_AUTO_EXPORT_DELAY_HOURS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.5, max=12, step=0.5, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_MORNING_REMINDER_ENABLED,
                default=defaults.get(CONF_MORNING_REMINDER_ENABLED, DEFAULT_MORNING_REMINDER_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_MORNING_REMINDER_TIME,
                default=defaults.get(CONF_MORNING_REMINDER_TIME, DEFAULT_MORNING_REMINDER_TIME),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_FORGOT_DEPARTURE_ENABLED,
                default=defaults.get(CONF_FORGOT_DEPARTURE_ENABLED, DEFAULT_FORGOT_DEPARTURE_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_FORGOT_DEPARTURE_OFFSET_MIN,
                default=defaults.get(
                    CONF_FORGOT_DEPARTURE_OFFSET_MIN, DEFAULT_FORGOT_DEPARTURE_OFFSET_MIN
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=240, step=5, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_ZONE_EXIT_GRACE_MIN,
                default=defaults.get(
                    CONF_ZONE_EXIT_GRACE_MIN, DEFAULT_ZONE_EXIT_GRACE_MIN
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=60, step=1, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
        }
    )


class WorktimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            title = (user_input.get("instance_name") or "").strip() or "Worktime Tracker"
            # Use a stable unique id per name so duplicates of the same name abort
            slug = "".join(c if c.isalnum() else "_" for c in title.lower()) or DOMAIN
            await self.async_set_unique_id(f"{DOMAIN}_{slug}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_build_user_schema(self.hass), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WorktimeOptionsFlow(config_entry)


class WorktimeOptionsFlow(OptionsFlow):
    """Options – allow editing all settings later."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = dict(self.entry.data)
        defaults.update(self.entry.options)
        return self.async_show_form(
            step_id="init", data_schema=_build_user_schema(self.hass, defaults)
        )
