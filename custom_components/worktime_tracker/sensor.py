"""Sensor entities for Worktime Tracker."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import WorktimeCoordinator


def _device_today(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_today")},
        name="Today",
        manufacturer="Worktime Tracker",
        model="Daily tracking",
    )


def _device_this_week(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_this_week")},
        name="This Week",
        manufacturer="Worktime Tracker",
        model="Weekly tracking",
    )


def _device_last_week(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_last_week")},
        name="Last Week",
        manufacturer="Worktime Tracker",
        model="Weekly tracking",
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WorktimeCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors: list[SensorEntity] = [
        ArrivalTimeSensor(coordinator, entry),
        PlannedEndTimeSensor(coordinator, entry),
        DepartureTimeSensor(coordinator, entry),
        HoursTodaySensor(coordinator, entry),
        HoursWeekSensor(coordinator, entry),
        OvertimeTodaySensor(coordinator, entry),
        OvertimeWeekSensor(coordinator, entry),
        TimeRemainingSensor(coordinator, entry),
        StatusSensor(coordinator, entry),
        LunchStatusSensor(coordinator, entry),
        *[WeekdaySensor(coordinator, entry, i, weeks_back=0) for i in range(5)],
        HoursLastWeekSensor(coordinator, entry),
        OvertimeLastWeekSensor(coordinator, entry),
        *[WeekdaySensor(coordinator, entry, i, weeks_back=1) for i in range(5)],
    ]
    async_add_entities(sensors)


class _BaseSensor(CoordinatorEntity[WorktimeCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _key: str = ""

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_device_info = _device_today(entry)


class _ThisWeekSensor(_BaseSensor):
    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device_this_week(entry)


class _LastWeekSensor(_BaseSensor):
    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_device_info = _device_last_week(entry)


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    local = dt_util.as_local(dt)
    return local.strftime("%H:%M")


class ArrivalTimeSensor(_BaseSensor):
    _key = "arrival_time"
    _attr_translation_key = "arrival_time"
    _attr_name = "Arrival time"
    _attr_icon = "mdi:login"

    @property
    def native_value(self) -> str:
        return _fmt(self.coordinator.arrival)


class PlannedEndTimeSensor(_BaseSensor):
    _key = "planned_end_time"
    _attr_translation_key = "planned_end_time"
    _attr_name = "Planned end time"
    _attr_icon = "mdi:flag-checkered"

    @property
    def native_value(self) -> str:
        return _fmt(self.coordinator.planned_end)


class DepartureTimeSensor(_BaseSensor):
    _key = "departure_time"
    _attr_translation_key = "departure_time"
    _attr_name = "Departure time"
    _attr_icon = "mdi:logout"

    @property
    def native_value(self) -> str:
        if self.coordinator.departure is not None:
            return _fmt(self.coordinator.departure)
        return _fmt(self.coordinator.planned_end)


class HoursTodaySensor(_BaseSensor):
    _key = "hours_today"
    _attr_translation_key = "hours_today"
    _attr_name = "Hours today"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-outline"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_today()


class HoursWeekSensor(_ThisWeekSensor):
    _key = "hours_week"
    _attr_translation_key = "hours_week"
    _attr_name = "Hours this week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-week"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_in_week()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        this_week = _week_breakdown(self.coordinator, weeks_back=0)
        last_week = _week_breakdown(self.coordinator, weeks_back=1)
        recent = sorted(
            [d for d in (last_week + this_week) if d["hours"] > 0],
            key=lambda d: d["date"],
        )[-5:]
        return {
            "weekly_target": self.coordinator.weekly_target,
            "this_week": this_week,
            "last_week": last_week,
            "recent_days": recent,
        }


class OvertimeTodaySensor(_BaseSensor):
    _key = "overtime_today"
    _attr_translation_key = "overtime_today"
    _attr_name = "Overtime today"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-plus-outline"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.overtime_today()


class OvertimeWeekSensor(_ThisWeekSensor):
    _key = "overtime_week"
    _attr_translation_key = "overtime_week"
    _attr_name = "Overtime this week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-plus-outline"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.overtime_this_week()


class TimeRemainingSensor(_BaseSensor):
    _key = "time_remaining"
    _attr_translation_key = "time_remaining"
    _attr_name = "Time remaining"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> int:
        secs = self.coordinator.time_remaining_seconds()
        return max(0, round(secs / 60))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        secs = self.coordinator.time_remaining_seconds()
        sign = "-" if secs < 0 else ""
        secs_abs = abs(secs)
        h, rem = divmod(secs_abs, 3600)
        m, _ = divmod(rem, 60)
        return {
            "seconds_remaining": secs,
            "human_readable": f"{sign}{h:d}h {m:02d}m",
            "is_overtime": self.coordinator.status() == "overtime",
        }


class StatusSensor(_BaseSensor):
    _key = "status"
    _attr_translation_key = "status"
    _attr_name = "Status"
    _attr_icon = "mdi:account-clock"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off_duty", "at_work", "done", "overtime"]

    @property
    def native_value(self) -> str:
        return self.coordinator.status()


class LunchStatusSensor(_BaseSensor):
    _key = "lunch_status"
    _attr_translation_key = "lunch_status"
    _attr_name = "Lunch status"
    _attr_icon = "mdi:food"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["yes", "no", "unknown"]

    @property
    def native_value(self) -> str:
        return self.coordinator.lunch_status


class HoursLastWeekSensor(_LastWeekSensor):
    _key = "hours_last_week"
    _attr_name = "Hours last week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-week"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.hours_worked_last_week()


class OvertimeLastWeekSensor(_LastWeekSensor):
    _key = "overtime_last_week"
    _attr_name = "Overtime last week"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-plus-outline"
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return self.coordinator.overtime_last_week()


_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


class WeekdaySensor(_BaseSensor):
    """One sensor per weekday (Mon–Fri) showing hours + times for the current week."""

    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-today"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry, weekday_index: int, weeks_back: int = 0) -> None:
        self._weekday_index = weekday_index
        self._weeks_back = weeks_back
        prefix = "last_" if weeks_back else ""
        self._key = f"{prefix}{_WEEKDAY_KEYS[weekday_index]}"
        self._attr_name = f"Last {_WEEKDAY_NAMES[weekday_index]}" if weeks_back else _WEEKDAY_NAMES[weekday_index]
        super().__init__(coordinator, entry)
        self._attr_device_info = _device_last_week(entry) if weeks_back else _device_this_week(entry)

    def _day_entry(self) -> dict[str, Any]:
        today = dt_util.now().date()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=self._weeks_back)
        target = monday + timedelta(days=self._weekday_index)
        target_iso = target.isoformat()

        for e in self.coordinator.history:
            if e.get("date") == target_iso:
                return e

        if target == today and self.coordinator.arrival is not None:
            return {
                "date": target_iso,
                "arrival": self.coordinator.arrival.isoformat(),
                "planned_end": self.coordinator.planned_end.isoformat() if self.coordinator.planned_end else None,
                "departure": self.coordinator.departure.isoformat() if self.coordinator.departure else None,
                "hours": self.coordinator.hours_worked_today(),
                "lunch": self.coordinator.lunch_status,
            }
        return {}

    @property
    def native_value(self) -> float:
        return round(float(self._day_entry().get("hours", 0.0)), 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        e = self._day_entry()
        if not e:
            return {"arrival": "—", "departure": "—", "lunch": "—", "date": "—"}

        def _parse(iso: str | None) -> str:
            if not iso:
                return "—"
            try:
                return dt_util.as_local(datetime.fromisoformat(iso)).strftime("%H:%M")
            except (ValueError, TypeError):
                return "—"

        departure = _parse(e.get("departure")) if e.get("departure") else _parse(e.get("planned_end"))
        return {
            "date": e.get("date", "—"),
            "arrival": _parse(e.get("arrival")),
            "departure": departure,
            "lunch": e.get("lunch", "—"),
        }


def _week_breakdown(coordinator: WorktimeCoordinator, weeks_back: int = 0) -> list[dict[str, Any]]:
    """Return Mon-Fri hours for ISO week (today - weeks_back weeks)."""
    today = dt_util.now().date()
    # Find Monday of the target week
    monday_today = today - timedelta(days=today.weekday())
    monday = monday_today - timedelta(weeks=weeks_back)
    days = []
    for offset in range(5):  # Mon-Fri
        d = monday + timedelta(days=offset)
        d_iso = d.isoformat()
        hours = 0.0
        for entry in coordinator.history:
            if entry.get("date") == d_iso:
                hours = float(entry.get("hours", 0.0))
                break
        # Add today's in-progress hours if it matches
        if d == today and coordinator.arrival is not None:
            already_logged = any(
                e.get("date") == d_iso and float(e.get("hours", 0)) > 0
                for e in coordinator.history
            )
            if not already_logged:
                hours = coordinator.hours_worked_today()
        _WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days.append({"date": d_iso, "weekday": _WEEKDAYS[d.weekday()], "hours": round(hours, 2)})
    return days
