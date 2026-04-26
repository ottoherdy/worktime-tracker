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
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import WorktimeCoordinator


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
        OvertimeWeekSensor(coordinator, entry),
        TimeRemainingSensor(coordinator, entry),
        StatusSensor(coordinator, entry),
        LunchStatusSensor(coordinator, entry),
    ]
    async_add_entities(sensors)


class _BaseSensor(CoordinatorEntity[WorktimeCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WorktimeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Worktime Tracker",
            manufacturer="Otto",
            model="Worktime Tracker",
            entry_type=None,
        )

    _key: str = ""


class ArrivalTimeSensor(_BaseSensor):
    _key = "arrival_time"
    _attr_translation_key = "arrival_time"
    _attr_name = "Arrival time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:login"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.arrival


class PlannedEndTimeSensor(_BaseSensor):
    _key = "planned_end_time"
    _attr_translation_key = "planned_end_time"
    _attr_name = "Planned end time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:flag-checkered"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.planned_end


class DepartureTimeSensor(_BaseSensor):
    _key = "departure_time"
    _attr_translation_key = "departure_time"
    _attr_name = "Departure time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:logout"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.departure


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


class HoursWeekSensor(_BaseSensor):
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
        # Provide a per-day breakdown for current and previous ISO week –
        # the dashboard ApexCharts card uses this directly.
        return {
            "weekly_target": self.coordinator.weekly_target,
            "this_week": _week_breakdown(self.coordinator, weeks_back=0),
            "last_week": _week_breakdown(self.coordinator, weeks_back=1),
        }


class OvertimeWeekSensor(_BaseSensor):
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
        days.append({"date": d_iso, "weekday": d.strftime("%a"), "hours": round(hours, 2)})
    return days
