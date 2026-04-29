"""Coordinator – contains all the business logic for Worktime Tracker."""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, time, timedelta
from typing import Any

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_SHORT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _round_quarter(hours: float) -> float:
    return math.ceil(hours * 4) / 4


def _hours_to_human(hours: float) -> str:
    total_min = round(hours * 60)
    if total_min == 0:
        return "—"
    h, m = divmod(total_min, 60)
    return f"{h}h {m:02d}m"

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACTION_LUNCH_NO,
    ACTION_LUNCH_YES,
    ACTION_TIMEREPORT_NO,
    ACTION_TIMEREPORT_YES,
    NOTIFICATION_TAG_TIMEREPORT,
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
    DEFAULT_AUTO_LUNCH_DEFAULT,
    DEFAULT_LUNCH_DEDUCTION,
    DEFAULT_LUNCH_TIME,
    DEFAULT_SHEETS_WORKSHEET,
    DEFAULT_WEEKLY_TARGET,
    DEFAULT_WORKDAY_HOURS,
    DOMAIN,
    EVENT_HISTORY_UPDATED,
    EVENT_NOTIFICATION_ACTION,
    LUNCH_NO,
    LUNCH_UNKNOWN,
    LUNCH_YES,
    NOTIFICATION_TAG,
    STATUS_AT_WORK,
    STATUS_DONE,
    STATUS_OFF_DUTY,
    STATUS_OVERTIME,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _parse_lunch_time(raw: str) -> time:
    """Parse 'HH:MM' or 'HH:MM:SS' into a time object."""
    parts = [int(p) for p in str(raw).split(":")]
    while len(parts) < 3:
        parts.append(0)
    return time(parts[0], parts[1], parts[2])


class WorktimeCoordinator(DataUpdateCoordinator):
    """Holds today's state, history and orchestrates everything."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._unsub_callbacks: list[Any] = []

        # Today state
        # _sessions: list of {"start": isoformat str, "end": isoformat str | None}
        self._sessions: list[dict[str, Any]] = []
        self._departure: datetime | None = None  # set only by manual log_departure
        self.planned_end: datetime | None = None
        self.lunch_status: str = LUNCH_UNKNOWN
        self.lunch_notification_sent: bool = False
        self.day_logged: bool = False
        self.current_date: date = dt_util.now().date()

        # History: list of dicts { date, sessions, arrival, planned_end, departure, lunch, hours }
        self.history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Session-derived properties
    # ------------------------------------------------------------------
    @property
    def arrival(self) -> datetime | None:
        if not self._sessions:
            return None
        return datetime.fromisoformat(self._sessions[0]["start"])

    @property
    def departure(self) -> datetime | None:
        return self._departure

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @property
    def options(self) -> dict[str, Any]:
        """Return merged config + options."""
        merged = dict(self.entry.data)
        merged.update(self.entry.options)
        return merged

    @property
    def person_entity(self) -> str:
        return self.options[CONF_PERSON_ENTITY]

    @property
    def work_zone(self) -> str:
        zone = self.options[CONF_WORK_ZONE]
        # Accept either "zone.otto_work" or "otto_work"
        if "." not in zone:
            zone = f"zone.{zone}"
        return zone

    @property
    def work_zone_name(self) -> str:
        """Return the zone object_id (without 'zone.' prefix)."""
        return self.work_zone.split(".", 1)[1]

    @property
    def notify_service(self) -> str | None:
        """Return notify service like 'mobile_app_otto_phone' (without notify. prefix)."""
        svc = self.options.get(CONF_NOTIFY_SERVICE)
        if not svc:
            return None
        if svc.startswith("notify."):
            svc = svc.split(".", 1)[1]
        return svc

    @property
    def lunch_time_obj(self) -> time:
        return _parse_lunch_time(self.options.get(CONF_LUNCH_TIME, DEFAULT_LUNCH_TIME))

    @property
    def workday_hours(self) -> float:
        return float(self.options.get(CONF_WORKDAY_HOURS, DEFAULT_WORKDAY_HOURS))

    @property
    def lunch_deduction(self) -> float:
        return float(self.options.get(CONF_LUNCH_DEDUCTION, DEFAULT_LUNCH_DEDUCTION))

    @property
    def weekly_target(self) -> float:
        return float(self.options.get(CONF_WEEKLY_TARGET, DEFAULT_WEEKLY_TARGET))

    @property
    def sheets_entry_id(self) -> str | None:
        entry_id = self.options.get(CONF_SHEETS_ENTRY)
        return entry_id if entry_id else None

    @property
    def sheets_worksheet(self) -> str:
        return self.options.get(CONF_SHEETS_WORKSHEET) or DEFAULT_SHEETS_WORKSHEET

    @property
    def auto_lunch_default(self) -> bool:
        return bool(self.options.get(CONF_AUTO_LUNCH_DEFAULT, DEFAULT_AUTO_LUNCH_DEFAULT))

    # ------------------------------------------------------------------
    # Initialization / shutdown
    # ------------------------------------------------------------------
    async def async_initialize(self) -> None:
        """Load history, register event subscriptions."""
        await self._async_load_history()

        # Restore today's state from history if we already logged today
        today = dt_util.now().date()
        for entry in self.history:
            if entry.get("date") == today.isoformat():
                self._restore_from_history_entry(entry)
                break

        # Subscribe to person state changes
        _LOGGER.info(
            "Worktime: tracking person='%s', work_zone='%s' (zone_name='%s')",
            self.person_entity, self.work_zone, self.work_zone_name,
        )
        self._unsub_callbacks.append(
            async_track_state_change_event(
                self.hass, [self.person_entity], self._handle_person_state_change
            )
        )

        # Subscribe to mobile_app_notification_action events
        self._unsub_callbacks.append(
            self.hass.bus.async_listen(
                EVENT_NOTIFICATION_ACTION, self._handle_notification_action
            )
        )

        # Lunch notification at configured time (every day)
        lt = self.lunch_time_obj
        self._unsub_callbacks.append(
            async_track_time_change(
                self.hass,
                self._handle_lunch_time,
                hour=lt.hour,
                minute=lt.minute,
                second=lt.second,
            )
        )

        # Daily roll-over at 03:00 (clears today's state if not already cleared)
        self._unsub_callbacks.append(
            async_track_time_change(
                self.hass, self._handle_day_rollover, hour=3, minute=0, second=0
            )
        )

        # Time report reminder every Friday at 16:00
        self._unsub_callbacks.append(
            async_track_time_change(
                self.hass, self._handle_timereport_time, hour=16, minute=0, second=0
            )
        )

        # Initial state check – maybe person is already at work
        state = self.hass.states.get(self.person_entity)
        if state and state.state.lower() == self.work_zone_name.lower() and self.arrival is None:
            await self.async_register_arrival(at_time=dt_util.now(), initial=True)

        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        for unsub in self._unsub_callbacks:
            try:
                unsub()
            except Exception:  # pylint: disable=broad-except
                pass
        self._unsub_callbacks.clear()

    # ------------------------------------------------------------------
    # DataUpdateCoordinator
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        """Periodic refresh – just rebuild derived data."""
        # Roll over if date changed
        now = dt_util.now()
        if now.date() != self.current_date:
            self.current_date = now.date()
            # If we never logged yesterday's day (e.g. left without GPS triggering), keep state
        return self.snapshot()

    # ------------------------------------------------------------------
    # State-change handlers
    # ------------------------------------------------------------------
    async def _handle_person_state_change(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        if new_state is None:
            return

        zone_name = self.work_zone_name
        old_s = old_state.state if old_state else "None"
        new_s = new_state.state
        _LOGGER.debug(
            "Worktime: person state change '%s' → '%s' (watching zone_name='%s')",
            old_s, new_s, zone_name,
        )

        was_at_work = bool(old_state and old_state.state.lower() == zone_name.lower())
        is_at_work = new_state.state.lower() == zone_name.lower()

        if not was_at_work and is_at_work:
            _LOGGER.info("Worktime: arrived at work zone (person state='%s')", new_s)
            await self.async_register_arrival(at_time=dt_util.now())
        elif was_at_work and not is_at_work:
            _LOGGER.info("Worktime: left work zone (person state='%s')", new_s)
            await self.async_zone_exit(at_time=dt_util.now())

    async def _handle_lunch_time(self, now: datetime) -> None:
        """Triggered at configured lunch time daily."""
        if not self._is_at_work():
            return
        if self.lunch_status != LUNCH_UNKNOWN:
            return
        if self.lunch_notification_sent:
            return
        await self._send_lunch_notification()

    async def _handle_day_rollover(self, now: datetime) -> None:
        """Daily 03:00 housekeeping."""
        # If departure not registered (forgot phone, GPS issue), persist what we have
        if self.arrival and not self.departure and not self.day_logged:
            _LOGGER.warning(
                "Worktime: day rolled over without departure for %s — auto-closing",
                self.current_date,
            )
            # Don't fabricate a departure; just reset for new day
        self._reset_day_state()
        self.async_set_updated_data(self.snapshot())

    async def _handle_timereport_time(self, now: datetime) -> None:
        """Triggered every Friday at 16:00."""
        if now.weekday() != 4:  # 4 = Friday
            return
        svc = self.notify_service
        if not svc:
            return
        try:
            await self.hass.services.async_call(
                "notify",
                svc,
                {
                    "title": "Time report",
                    "message": "Have you submitted your time report?",
                    "data": {
                        "tag": NOTIFICATION_TAG_TIMEREPORT,
                        "actions": [
                            {"action": ACTION_TIMEREPORT_YES, "title": "Yes, done"},
                            {"action": ACTION_TIMEREPORT_NO, "title": "Not yet"},
                        ],
                    },
                },
                blocking=False,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: failed to send time report notification: %s", exc)

    async def _handle_notification_action(self, event: Event) -> None:
        action = event.data.get("action")
        if action == ACTION_LUNCH_YES:
            await self.async_set_lunch(LUNCH_YES)
        elif action == ACTION_LUNCH_NO:
            await self.async_set_lunch(LUNCH_NO)
        elif action == ACTION_TIMEREPORT_YES:
            await self._async_append_to_sheet()

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    async def async_register_arrival(
        self,
        at_time: datetime | None = None,
        manual: bool = False,
        initial: bool = False,
    ) -> None:
        if at_time is None:
            at_time = dt_util.now()
        # If last session is still open (already at work), ignore
        if self._sessions and self._sessions[-1].get("end") is None and not manual:
            return
        self._sessions.append({"start": at_time.isoformat(), "end": None})
        self.day_logged = False
        # planned_end is always based on first arrival
        first_arrival = datetime.fromisoformat(self._sessions[0]["start"])
        self.planned_end = first_arrival + timedelta(hours=self.workday_hours)
        self.lunch_notification_sent = False
        self.current_date = at_time.date()
        _LOGGER.info("Worktime: arrival registered at %s", at_time.isoformat())
        await self._async_save_today()
        self.async_set_updated_data(self.snapshot())

    async def async_zone_exit(self, at_time: datetime | None = None) -> None:
        """Zone exit — close current session but do NOT set official departure."""
        if at_time is None:
            at_time = dt_util.now()
        if not self._sessions:
            return
        last = self._sessions[-1]
        if last.get("end") is not None:
            return
        last["end"] = at_time.isoformat()
        _LOGGER.info("Worktime: zone exit at %s — session paused", at_time.isoformat())
        await self._async_save_today()
        self.async_set_updated_data(self.snapshot())

    async def async_register_departure(
        self,
        at_time: datetime | None = None,
        manual: bool = False,
    ) -> None:
        if at_time is None:
            at_time = dt_util.now()
        if not self._sessions:
            _LOGGER.debug("Worktime: departure ignored — no arrival registered")
            return
        # Close current open session if any
        last = self._sessions[-1]
        if last.get("end") is None:
            last["end"] = at_time.isoformat()
        self._departure = at_time

        # If lunch unknown at departure, fall back to default
        if self.lunch_status == LUNCH_UNKNOWN:
            self.lunch_status = LUNCH_YES if self.auto_lunch_default else LUNCH_NO
            self._recompute_planned_end()

        await self._async_log_today_to_history()
        await self._async_save_today()
        self.async_set_updated_data(self.snapshot())

    async def async_set_lunch(self, status: str) -> None:
        if status not in (LUNCH_YES, LUNCH_NO):
            return
        self.lunch_status = status
        self._recompute_planned_end()
        await self._async_save_today()
        self.async_set_updated_data(self.snapshot())

    async def async_reset_today(self) -> None:
        self._reset_day_state()
        await self._async_save_today()
        self.async_set_updated_data(self.snapshot())

    async def async_edit_day(
        self,
        target_date: date,
        arrival: str | None = None,
        departure: str | None = None,
        lunch: str | None = None,
    ) -> None:
        """Edit a historical day entry. Times as HH:MM strings."""
        today = dt_util.now().date()
        target_iso = target_date.isoformat()

        def _parse_time(t: str, ref_date: date) -> datetime:
            h, m = map(int, t.split(":"))
            local = datetime(ref_date.year, ref_date.month, ref_date.day, h, m)
            return dt_util.as_utc(dt_util.as_local(local))

        # Find or create the entry
        entry: dict[str, Any] | None = None
        for e in self.history:
            if e.get("date") == target_iso:
                entry = e
                break
        if entry is None:
            entry = {"date": target_iso, "arrival": None, "planned_end": None, "departure": None, "lunch": LUNCH_UNKNOWN, "hours": 0.0}
            self.history.append(entry)

        if arrival:
            arr_dt = _parse_time(arrival, target_date)
            entry["arrival"] = arr_dt.isoformat()
        if departure:
            dep_dt = _parse_time(departure, target_date)
            entry["departure"] = dep_dt.isoformat()
        if lunch:
            entry["lunch"] = lunch

        # Recalculate hours if we have both arrival and departure
        if entry.get("arrival") and entry.get("departure"):
            arr = datetime.fromisoformat(entry["arrival"])
            dep = datetime.fromisoformat(entry["departure"])
            hours = (dep - arr).total_seconds() / 3600.0
            if entry.get("lunch") == LUNCH_YES:
                hours -= self.lunch_deduction
            entry["hours"] = max(0.0, round(hours, 2))
            entry["sessions"] = [{"start": entry["arrival"], "end": entry["departure"]}]

        await self._async_save_history()

        # If editing today, sync in-memory state
        if target_date == today:
            self._restore_from_history_entry(entry)

        self.async_set_updated_data(self.snapshot())
        _LOGGER.info("Worktime: edited day %s → %s", target_iso, entry)

        # Push updated row to Sheets (marked as edited)
        await self._async_append_to_sheet(entry=entry, edited=True)

    async def async_export_history(self) -> None:
        """Re-send today's entry to Google Sheets."""
        if self.arrival is None:
            _LOGGER.info("Worktime: nothing to export for today")
            return
        await self._async_append_to_sheet()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_at_work(self) -> bool:
        state = self.hass.states.get(self.person_entity)
        return bool(state and state.state.lower() == self.work_zone_name.lower())

    def _recompute_planned_end(self) -> None:
        if self.arrival is None:
            return
        # If lunch was taken: full workday_hours (e.g. 8.5h with 30min lunch = 8h work)
        # If lunch NOT taken: subtract lunch_deduction (e.g. 8.5 - 0.5 = 8h total => done 30 min earlier)
        hours = self.workday_hours
        if self.lunch_status == LUNCH_NO:
            hours -= self.lunch_deduction
        self.planned_end = self.arrival + timedelta(hours=hours)

    def _reset_day_state(self) -> None:
        self._sessions = []
        self._departure = None
        self.planned_end = None
        self.lunch_status = LUNCH_UNKNOWN
        self.lunch_notification_sent = False
        self.day_logged = False
        self.current_date = dt_util.now().date()

    def _restore_from_history_entry(self, entry: dict[str, Any]) -> None:
        try:
            sessions = entry.get("sessions")
            if sessions:
                self._sessions = sessions
            else:
                # Backward compat: old format with flat arrival/departure
                arrival_iso = entry.get("arrival")
                departure_iso = entry.get("departure")
                if arrival_iso:
                    self._sessions = [{"start": arrival_iso, "end": departure_iso}]
                else:
                    self._sessions = []
            self.planned_end = (
                datetime.fromisoformat(entry["planned_end"])
                if entry.get("planned_end")
                else None
            )
            departure_iso = entry.get("departure")
            self._departure = datetime.fromisoformat(departure_iso) if departure_iso else None
            self.lunch_status = entry.get("lunch", LUNCH_UNKNOWN)
            self.day_logged = bool(departure_iso)
            self.current_date = date.fromisoformat(entry["date"])
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Worktime: failed to restore today's state: %s", exc)

    async def _send_lunch_notification(self) -> None:
        svc = self.notify_service
        if not svc:
            _LOGGER.warning("Worktime: lunch time but no notify service configured")
            return
        message = "Did you have lunch today?"
        title = "Lunch check"
        try:
            await self.hass.services.async_call(
                "notify",
                svc,
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": NOTIFICATION_TAG,
                        "actions": [
                            {"action": ACTION_LUNCH_YES, "title": "Yes"},
                            {"action": ACTION_LUNCH_NO, "title": "No"},
                        ],
                    },
                },
                blocking=False,
            )
            self.lunch_notification_sent = True
            await self._async_save_today()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: failed to send lunch notification: %s", exc)

    # ------------------------------------------------------------------
    # Computed values exposed to entities
    # ------------------------------------------------------------------
    def hours_worked_today(self) -> float:
        if not self._sessions:
            return 0.0
        now = dt_util.now()
        total = 0.0
        for s in self._sessions:
            start = datetime.fromisoformat(s["start"])
            end = datetime.fromisoformat(s["end"]) if s.get("end") else now
            total += (end - start).total_seconds() / 3600.0
        if self.lunch_status == LUNCH_YES:
            total -= self.lunch_deduction
        return max(0.0, round(total, 2))

    def hours_worked_in_week(self, target_date: date | None = None) -> float:
        """Sum hours for the ISO week of target_date (default: today)."""
        target_date = target_date or dt_util.now().date()
        year, week, _ = target_date.isocalendar()
        total = 0.0
        for entry in self.history:
            try:
                d = date.fromisoformat(entry["date"])
            except Exception:
                continue
            y, w, _ = d.isocalendar()
            if y == year and w == week:
                total += float(entry.get("hours", 0.0))
        # Add today's live hours if the day is still in progress
        today = dt_util.now().date()
        if today.isocalendar()[:2] == (year, week):
            day_complete = any(
                e.get("date") == today.isoformat() and e.get("departure")
                for e in self.history
            )
            if not day_complete and self._sessions:
                # Subtract what was already counted from the in-progress history entry (hours=0)
                total += self.hours_worked_today()
        return round(total, 2)

    @property
    def daily_net_target(self) -> float:
        return round(self.workday_hours - self.lunch_deduction, 2)

    def hours_worked_last_week(self) -> float:
        last_week_date = dt_util.now().date() - timedelta(weeks=1)
        return self.hours_worked_in_week(target_date=last_week_date)

    def overtime_last_week(self) -> float:
        last_week_date = dt_util.now().date() - timedelta(weeks=1)
        monday = last_week_date - timedelta(days=last_week_date.weekday())
        days_with_work = 0
        for offset in range(5):
            d = monday + timedelta(days=offset)
            d_iso = d.isoformat()
            if any(e.get("date") == d_iso and float(e.get("hours", 0)) > 0 for e in self.history):
                days_with_work += 1
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_last_week() - expected, 2)

    def overtime_today(self) -> float:
        return round(self.hours_worked_today() - self.daily_net_target, 2)

    def overtime_this_week(self) -> float:
        """Overtime vs expected hours for days worked so far this week."""
        today = dt_util.now().date()
        monday = today - timedelta(days=today.weekday())
        days_with_work = 0
        for offset in range(5):
            d = monday + timedelta(days=offset)
            if d > today:
                break
            d_iso = d.isoformat()
            has_work = any(
                e.get("date") == d_iso and float(e.get("hours", 0)) > 0
                for e in self.history
            )
            if not has_work and d == today and self.arrival is not None:
                has_work = True
            if has_work:
                days_with_work += 1
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_in_week() - expected, 2)

    def week_breakdown(self, weeks_back: int = 0) -> list[dict[str, Any]]:
        """Return Mon–Fri data for the week offset by weeks_back."""
        today = dt_util.now().date()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_back)
        result = []
        for offset in range(5):
            d = monday + timedelta(days=offset)
            d_iso = d.isoformat()
            entry: dict[str, Any] | None = None
            for e in self.history:
                if e.get("date") == d_iso:
                    entry = e
                    break
            if entry is None and d == today and self.arrival is not None:
                entry = {
                    "date": d_iso,
                    "arrival": self.arrival.isoformat(),
                    "planned_end": self.planned_end.isoformat() if self.planned_end else None,
                    "departure": self.departure.isoformat() if self.departure else None,
                    "lunch": self.lunch_status,
                    "hours": self.hours_worked_today(),
                }
            if entry:
                hours = float(entry.get("hours", 0.0))
                def _p(iso: str | None) -> str:
                    if not iso:
                        return "—"
                    try:
                        return dt_util.as_local(datetime.fromisoformat(iso)).strftime("%H:%M")
                    except Exception:
                        return "—"
                dep_iso = entry.get("departure") or entry.get("planned_end")
                result.append({
                    "date": d_iso,
                    "weekday": _SHORT_DAYS[d.weekday()],
                    "arrival": _p(entry.get("arrival")),
                    "departure": _p(dep_iso),
                    "lunch": entry.get("lunch", "—"),
                    "hours": round(hours, 2),
                    "human_readable": _hours_to_human(hours),
                })
            else:
                result.append({
                    "date": d_iso,
                    "weekday": _SHORT_DAYS[d.weekday()],
                    "arrival": "—",
                    "departure": "—",
                    "lunch": "—",
                    "hours": 0.0,
                    "human_readable": "—",
                })
        return result

    def recent_days(self, count: int = 14) -> list[dict[str, Any]]:
        """Return the last `count` calendar days that have data, newest first."""
        today = dt_util.now().date()
        result = []
        for offset in range(count):
            d = today - timedelta(days=offset)
            d_iso = d.isoformat()
            entry: dict[str, Any] | None = None
            for e in self.history:
                if e.get("date") == d_iso:
                    entry = e
                    break
            if entry is None and d == today and self.arrival is not None:
                entry = {
                    "date": d_iso,
                    "arrival": self.arrival.isoformat(),
                    "planned_end": self.planned_end.isoformat() if self.planned_end else None,
                    "departure": self.departure.isoformat() if self.departure else None,
                    "lunch": self.lunch_status,
                    "hours": self.hours_worked_today(),
                }
            if not entry:
                continue

            def _p(iso: str | None) -> str:
                if not iso:
                    return "—"
                try:
                    return dt_util.as_local(datetime.fromisoformat(iso)).strftime("%H:%M")
                except Exception:
                    return "—"

            hours = float(entry.get("hours", 0.0))
            dep_iso = entry.get("departure") or entry.get("planned_end")
            result.append({
                "date": d_iso,
                "weekday": _SHORT_DAYS[d.weekday()],
                "arrival": _p(entry.get("arrival")),
                "departure": _p(dep_iso),
                "lunch": entry.get("lunch", "—"),
                "hours": round(hours, 2),
                "human_readable": _hours_to_human(hours),
            })
        return result

    def time_remaining_seconds(self) -> int:
        if self.arrival is None or self.planned_end is None:
            return 0
        if self.departure is not None:
            return 0
        delta = self.planned_end - dt_util.now()
        return int(delta.total_seconds())

    def status(self) -> str:
        if self.arrival is None:
            return STATUS_OFF_DUTY
        if self.departure is not None:
            return STATUS_DONE
        if self.planned_end and dt_util.now() >= self.planned_end:
            return STATUS_OVERTIME
        return STATUS_AT_WORK

    def snapshot(self) -> dict[str, Any]:
        return {
            "arrival": self.arrival,
            "planned_end": self.planned_end,
            "departure": self.departure,
            "lunch": self.lunch_status,
            "hours_today": self.hours_worked_today(),
            "hours_week": self.hours_worked_in_week(),
            "overtime_today": self.overtime_today(),
            "overtime_week": self.overtime_this_week(),
            "remaining_seconds": self.time_remaining_seconds(),
            "status": self.status(),
            "history": self.history,
            "weekly_target": self.weekly_target,
            "workday_hours": self.workday_hours,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    async def _async_load_history(self) -> None:
        data = await self._store.async_load() or {}
        self.history = data.get("history", [])
        # Trim to last 180 days to stay small
        if len(self.history) > 180:
            self.history = self.history[-180:]

    async def _async_save_history(self) -> None:
        await self._store.async_save({"history": self.history})

    async def _async_save_today(self) -> None:
        """Upsert today's working state into history (so a restart keeps state)."""
        today_iso = self.current_date.isoformat()
        entry = {
            "date": today_iso,
            "sessions": list(self._sessions),
            "arrival": self._sessions[0]["start"] if self._sessions else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "departure": self._departure.isoformat() if self._departure else None,
            "lunch": self.lunch_status,
            "hours": self.hours_worked_today() if self._departure else 0.0,
        }
        # Only keep "complete" days as historical, but persist in-progress too for restore
        replaced = False
        for i, existing in enumerate(self.history):
            if existing.get("date") == today_iso:
                self.history[i] = entry
                replaced = True
                break
        if not replaced:
            self.history.append(entry)
        await self._async_save_history()
        self.hass.bus.async_fire(EVENT_HISTORY_UPDATED, {"date": today_iso})

    async def _async_log_today_to_history(self) -> None:
        """Called on departure: write final values to history."""
        if self.day_logged:
            return
        await self._async_save_today()
        self.day_logged = True

    def _format_time(self, dt_obj: datetime | None) -> str:
        if not dt_obj:
            return ""
        local = dt_util.as_local(dt_obj)
        return local.strftime("%H:%M")

    async def _async_append_to_sheet(
        self,
        entry: dict[str, Any] | None = None,
        edited: bool = False,
    ) -> None:
        """Append a row to Google Sheets. Uses today's state when entry is None."""
        entry_id = self.sheets_entry_id
        if not entry_id:
            return
        if not self.hass.services.has_service("google_sheets", "append_sheet"):
            _LOGGER.warning(
                "Worktime: google_sheets integration not installed — skipping Sheets log"
            )
            return

        if entry is None:
            target_date = self.current_date
            arrival = self.arrival
            planned_end = self.planned_end
            departure = self.departure
            lunch = self.lunch_status
            hours = self.hours_worked_today()
        else:
            try:
                target_date = date.fromisoformat(entry["date"])
                arrival = datetime.fromisoformat(entry["arrival"]) if entry.get("arrival") else None
                planned_end = datetime.fromisoformat(entry["planned_end"]) if entry.get("planned_end") else None
                departure = datetime.fromisoformat(entry["departure"]) if entry.get("departure") else None
                lunch = entry.get("lunch", LUNCH_UNKNOWN)
                hours = float(entry.get("hours", 0.0))
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("Worktime: failed to parse entry for Sheets: %s", exc)
                return

        overtime = round(hours - self.daily_net_target, 2)

        row = {
            "Date": target_date.isoformat(),
            "Weekday": _WEEKDAYS[target_date.weekday()],
            "Arrival": self._format_time(arrival),
            "Planned end": self._format_time(planned_end),
            "Departure": self._format_time(departure),
            "Lunch": lunch,
            "Hours": hours,
            "Hours (rounded)": f"{_round_quarter(hours):.2f}h",
            "Overtime": overtime,
            "Edited": "yes" if edited else "no",
        }
        try:
            await self.hass.services.async_call(
                "google_sheets",
                "append_sheet",
                {
                    "config_entry": entry_id,
                    "worksheet": self.sheets_worksheet,
                    "data": row,
                },
                blocking=True,
            )
            _LOGGER.info("Worktime: appended day to Sheets (%s)", self.sheets_worksheet)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Worktime: Google Sheets append failed: %s", exc)
