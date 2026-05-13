"""Config flow for Worktime Tracker."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_DEPARTURE_ENABLED,
    CONF_AUTO_DEPARTURE_TIME,
    CONF_AUTO_EXPORT_DELAY_HOURS,
    CONF_AUTO_EXPORT_ENABLED,
    CONF_AUTO_LUNCH_DEFAULT,
    CONF_LUNCH_DEDUCTION,
    CONF_LUNCH_TIME,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON_ENTITY,
    CONF_SHEETS_ENTRY,
    CONF_SHEETS_WORKSHEET,
    CONF_WEEKLY_TARGET,
    CONF_WORK_ZONE,
    CONF_WORKDAY_HOURS,
    DEFAULT_AUTO_DEPARTURE_ENABLED,
    DEFAULT_AUTO_DEPARTURE_TIME,
    DEFAULT_AUTO_EXPORT_DELAY_HOURS,
    DEFAULT_AUTO_EXPORT_ENABLED,
    DEFAULT_AUTO_LUNCH_DEFAULT,
    DEFAULT_LUNCH_DEDUCTION,
    DEFAULT_LUNCH_TIME,
    DEFAULT_SHEETS_WORKSHEET,
    DEFAULT_WEEKLY_TARGET,
    DEFAULT_WORKDAY_HOURS,
    DOMAIN,
)


def _build_user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PERSON_ENTITY, default=defaults.get(CONF_PERSON_ENTITY)
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
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
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
                CONF_SHEETS_ENTRY, default=defaults.get(CONF_SHEETS_ENTRY, "")
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
        }
    )


class WorktimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        # Single-instance enforcement
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(title="Worktime Tracker", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_build_user_schema(), errors=errors
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
            step_id="init", data_schema=_build_user_schema(defaults)
        )
