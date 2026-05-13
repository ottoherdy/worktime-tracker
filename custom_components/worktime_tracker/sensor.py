"""Sensor entities for Worktime Tracker."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from datetime import timedelta

from .const import DOMAIN
from .coordinator import WorktimeCoordinator


def _hours_to_human(hours: float) -> str:
    total_min = round(hours * 60)
    if total_min == 0:
        return "—"
    h, m = divmod(total_min, 60)
    return f"{h}h {m:02d}m"


def _device(entry: ConfigEntry, suffix: str, name: str, model: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{suffix}")},
        name=name,
        manufacturer="Worktime Tracker",
        model=model,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WorktimeCoordinator = entry.runtime_data
    async_add_entities([
        TodaySensor(coordinator, entry),
        StatusSensor(coordinator, entry),
        ThisWeekSensor(coordinator, entry),
        LastWeekSensor(coordinator, entry),
        ThisMonthSensor(coordinator, entry),
        LastMonthSensor(coordinator, entry),
    ])


class _Base(CoordinatorEntity[WorktimeCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _key: str = ""

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"


class TodaySensor(_Base):
    """Main daily sensor. Self-ticks every 30 s for live countdown."""

    _key = "hours_today"
    _attr_name = "Hours today"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-outline"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "today", "Today", "Daily tracking")
        self._unsub_tick = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Self-tick every 30 s so countdown updates without coordinator push
        self._unsub_tick = async_track_time_interval(
            self.hass,
            self._handle_tick,
            timedelta(seconds=30),
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_tick is not None:
            self._unsub_tick()
            self._unsub_tick = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_tick(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_today()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator

        def _fmt(dt: datetime | None) -> str:
            if dt is None:
                return "—"
            return dt_util.as_local(dt).strftime("%H:%M")

        hours = c.hours_worked_today()
        secs = c.time_remaining_seconds()
        sign = "-" if secs < 0 else ""
        secs_abs = abs(secs)
        rh, rem = divmod(secs_abs, 3600)
        rm, _ = divmod(rem, 60)
        time_remaining = f"{sign}{rh}h {rm:02d}m" if c.arrival else "—"

        return {
            "arrival": _fmt(c.arrival),
            "departure": _fmt(c.departure) if c.departure else _fmt(c.planned_end),
            "planned_end": _fmt(c.planned_end),
            "lunch": "" if c.lunch_status == "unknown" else c.lunch_status,
            "hours": hours,
            "human_readable": _hours_to_human(hours),
            "overtime": c.overtime_today(),
            "time_remaining": time_remaining,
            "status": c.status(),
            "recent_days": c.recent_days(60),
            "daily_net_target": c.daily_net_target,
        }


class StatusSensor(_Base):
    _key = "status"
    _attr_name = "Status"
    _attr_icon = "mdi:account-clock"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off_duty", "at_work", "done", "overtime"]

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "today", "Today", "Daily tracking")

    @property
    def native_value(self) -> str:
        return self.coordinator.status()


class ThisWeekSensor(_Base):
    _key = "hours_this_week"
    _attr_name = "Hours this week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-week"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "this_week", "This Week", "Weekly tracking")

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_in_week()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "hours": self.coordinator.hours_worked_in_week(),
            "overtime": self.coordinator.overtime_this_week(),
            "weekly_target": self.coordinator.weekly_target,
            "days": self.coordinator.week_breakdown(weeks_back=0),
        }


class LastWeekSensor(_Base):
    _key = "hours_last_week"
    _attr_name = "Hours last week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-week"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "last_week", "Last Week", "Weekly tracking")

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_last_week()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "hours": self.coordinator.hours_worked_last_week(),
            "overtime": self.coordinator.overtime_last_week(),
            "days": self.coordinator.week_breakdown(weeks_back=1),
        }


class ThisMonthSensor(_Base):
    _key = "hours_this_month"
    _attr_name = "Hours this month"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-month"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "this_month", "This Month", "Monthly tracking")

    @property
    def native_value(self) -> float:
        today = dt_util.now().date()
        return self.coordinator.hours_worked_in_month(today.year, today.month)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        hours = self.coordinator.hours_worked_in_month(today.year, today.month)
        return {
            "hours": hours,
            "human_readable": _hours_to_human(hours),
            "overtime": self.coordinator.overtime_this_month(),
            "month": self.coordinator.month_name(0),
        }


class LastMonthSensor(_Base):
    _key = "hours_last_month"
    _attr_name = "Hours last month"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-month"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device(entry, "last_month", "Last Month", "Monthly tracking")

    @property
    def native_value(self) -> float:
        today = dt_util.now().date()
        if today.month == 1:
            return self.coordinator.hours_worked_in_month(today.year - 1, 12)
        return self.coordinator.hours_worked_in_month(today.year, today.month - 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1
        hours = self.coordinator.hours_worked_in_month(year, month)
        return {
            "hours": hours,
            "human_readable": _hours_to_human(hours),
            "overtime": self.coordinator.overtime_last_month(),
            "month": self.coordinator.month_name(1),
        }
