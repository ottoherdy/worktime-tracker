"""Coordinator – contains all the business logic for Worktime Tracker."""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import date, datetime, time, timedelta
from typing import Any

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_SHORT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_LOGGER = logging.getLogger(__name__)


def _round_quarter(hours: float) -> float:
    return math.ceil(hours * 4) / 4


def _hours_to_human(hours: float) -> str:
    total_min = round(hours * 60)
    if total_min == 0:
        return "—"
    h, m = divmod(total_min, 60)
    return f"{h}h {m:02d}m"


def _parse_lunch_time(raw: str) -> time:
    """Parse 'HH:MM' or 'HH:MM:SS' into a time object."""
    parts = [int(p) for p in str(raw).split(":")]
    while len(parts) < 3:
        parts.append(0)
    return time(parts[0], parts[1], parts[2])


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACTION_DEPARTURE_NOW,
    ACTION_LUNCH_NO,
    ACTION_LUNCH_YES,
    ACTION_MORNING_ARRIVE,
    ACTION_MORNING_HOME,
    ACTION_MORNING_SICK,
    ACTION_TIMEREPORT_YES,
    NOTIFICATION_TAG_DEPARTURE,
    NOTIFICATION_TAG_MORNING,
    NOTIFICATION_TAG_TIMEREPORT,
    ACTION_TIMEREPORT_NO,
    CONF_AUTO_DEPARTURE_ENABLED,
    CONF_AUTO_DEPARTURE_TIME,
    CONF_AUTO_EXPORT_DELAY_HOURS,
    CONF_AUTO_EXPORT_ENABLED,
    CONF_AUTO_LUNCH_DEFAULT,
    CONF_ARRIVAL_MARGIN_MINUTES,
    CONF_DEPARTURE_MARGIN_MINUTES,
    CONF_FORGOT_DEPARTURE_ENABLED,
    CONF_FORGOT_DEPARTURE_OFFSET_MIN,
    CONF_ZONE_EXIT_GRACE_MIN,
    CONF_LUNCH_DEDUCTION,
    CONF_MORNING_REMINDER_ENABLED,
    CONF_MORNING_REMINDER_TIME,
    CONF_LUNCH_TIME,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON,
    CONF_SHEETS_ENTRY_ID,
    CONF_SHEETS_WORKSHEET,
    CONF_WEEKLY_TARGET,
    CONF_WORK_ZONE,
    CONF_WORKDAY_HOURS,
    DAY_TYPE_FLEX,
    DAY_TYPE_HOME,
    DAY_TYPE_NORMAL,
    DAY_TYPE_OFF,
    DAY_TYPE_SICK,
    DEFAULT_ARRIVAL_MARGIN_MINUTES,
    DEFAULT_AUTO_DEPARTURE_ENABLED,
    DEFAULT_AUTO_DEPARTURE_TIME,
    DEFAULT_AUTO_EXPORT_DELAY_HOURS,
    DEFAULT_AUTO_EXPORT_ENABLED,
    DEFAULT_AUTO_LUNCH_DEFAULT,
    DEFAULT_DEPARTURE_MARGIN_MINUTES,
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
    MAX_MARGIN_MINUTES,
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
)


class WorktimeCoordinator(DataUpdateCoordinator):
    """Holds today's state, history and orchestrates everything.

    Push-only updates via async_set_updated_data — no polling interval.
    TodaySensor self-ticks every 30 s for countdown refresh.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # No update_interval — pure push via async_set_updated_data
        )
        self.hass = hass
        self.entry = entry
        # Per-entry storage so multiple instances don't clobber each other.
        # The legacy single-file key (worktime_tracker.history) is kept around
        # for one-time migration on the oldest entry — see _async_load().
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}"
        )
        self._legacy_store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._unsub: list[Any] = []
        self._unsub_auto_export: Any = None
        self._unsub_forgot_departure: Any = None
        self._unsub_zone_exit: Any = None
        # Notification de-dup flags reset at rollover
        self._morning_notified: bool = False
        self._forgot_departure_notified: bool = False

        # Today state
        self.arrival: datetime | None = None
        self._departure: datetime | None = None
        self.lunch_status: str = LUNCH_UNKNOWN
        self._lunch_notified: bool = False
        self._today_date: date | None = None  # which date the above state belongs to
        self._auto_departure_enabled: bool = False
        self._arrival_margin_minutes: int = DEFAULT_ARRIVAL_MARGIN_MINUTES
        self._departure_margin_minutes: int = DEFAULT_DEPARTURE_MARGIN_MINUTES

        # Persisted data
        self.history: list[dict[str, Any]] = []          # completed normal work days
        self.leave_records: list[dict[str, Any]] = []    # sick / leave days

        # Per-date Sheets sync state: {iso_date: {"rev": int, "fp": str, "ts": iso}}.
        # Tracks what we last pushed so export_all can skip unchanged days and
        # bump Rev when something has changed. Sheets export is fully optional —
        # this dict stays empty until the user actually uses it.
        self.sheets_sync: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def departure(self) -> datetime | None:
        return self._departure

    @property
    def options(self) -> dict[str, Any]:
        merged = dict(self.entry.data)
        merged.update(self.entry.options)
        return merged

    @property
    def person_entity(self) -> str:
        return self.options[CONF_PERSON]

    @property
    def work_zone(self) -> str:
        zone = self.options[CONF_WORK_ZONE]
        if "." not in zone:
            zone = f"zone.{zone}"
        return zone

    @property
    def work_zone_name(self) -> str:
        return self.work_zone.split(".", 1)[1]

    @property
    def instance_slug(self) -> str:
        """Stable slug derived from the entry's instance_name. Used to
        suffix notification actions and tags so a multi-instance setup
        doesn't echo every action across all coordinators."""
        name = self.entry.data.get("instance_name") or self.entry.title or ""
        slug = "".join(c if c.isalnum() else "_" for c in name.lower())
        return slug or DOMAIN

    def _scoped(self, base: str) -> str:
        """Append the instance slug so notification actions and tags
        are unique per coordinator."""
        return f"{base}__{self.instance_slug}"

    def _matches_my_action(self, action: str, base: str) -> bool:
        """True if a notification-action event belongs to this coordinator
        and matches the given base action constant. Tolerates legacy
        notifications fired before v2.9.1 that lack the slug suffix —
        only the oldest entry replies in that case, mirroring the legacy
        single-instance behaviour."""
        if not action:
            return False
        if action == self._scoped(base):
            return True
        if action == base:
            return self._is_oldest_entry()
        return False

    def _is_at_work(self, state_value: str | None) -> bool:
        """True if a person.* state value indicates presence in our work zone.

        HA stores the zone's *friendly name* in person state — not the
        entity_id slug. For 'zone.ellens_jobb' with friendly name
        'Ellens Jobb', person.foo.state will be 'Ellens Jobb', not
        'ellens_jobb'. Comparing only against the slug silently broke
        zone detection for any zone whose friendly name had spaces or
        differed in case from its slug.
        """
        if not state_value:
            return False
        v = state_value.lower()
        if v == self.work_zone_name.lower():
            return True
        zone_state = self.hass.states.get(self.work_zone)
        friendly = zone_state and zone_state.attributes.get("friendly_name")
        return bool(friendly and v == friendly.lower())

    @property
    def notify_service(self) -> str | None:
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
    def morning_reminder_enabled(self) -> bool:
        return bool(self.options.get(
            CONF_MORNING_REMINDER_ENABLED, DEFAULT_MORNING_REMINDER_ENABLED
        ))

    @property
    def morning_reminder_time_obj(self) -> time:
        return _parse_lunch_time(self.options.get(
            CONF_MORNING_REMINDER_TIME, DEFAULT_MORNING_REMINDER_TIME
        ))

    @property
    def forgot_departure_enabled(self) -> bool:
        return bool(self.options.get(
            CONF_FORGOT_DEPARTURE_ENABLED, DEFAULT_FORGOT_DEPARTURE_ENABLED
        ))

    @property
    def forgot_departure_offset_minutes(self) -> int:
        return int(self.options.get(
            CONF_FORGOT_DEPARTURE_OFFSET_MIN, DEFAULT_FORGOT_DEPARTURE_OFFSET_MIN
        ))

    @property
    def zone_exit_grace_minutes(self) -> int:
        return int(self.options.get(
            CONF_ZONE_EXIT_GRACE_MIN, DEFAULT_ZONE_EXIT_GRACE_MIN
        ))

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
        val = self.options.get(CONF_SHEETS_ENTRY_ID)
        return val if val else None

    @property
    def sheets_worksheet(self) -> str:
        return self.options.get(CONF_SHEETS_WORKSHEET) or DEFAULT_SHEETS_WORKSHEET

    @property
    def auto_lunch_default(self) -> bool:
        return bool(self.options.get(CONF_AUTO_LUNCH_DEFAULT, DEFAULT_AUTO_LUNCH_DEFAULT))

    @property
    def auto_departure_enabled(self) -> bool:
        return self._auto_departure_enabled

    @property
    def auto_departure_time_obj(self) -> time:
        return _parse_lunch_time(
            self.options.get(CONF_AUTO_DEPARTURE_TIME, DEFAULT_AUTO_DEPARTURE_TIME)
        )

    @property
    def auto_export_enabled(self) -> bool:
        return bool(self.options.get(CONF_AUTO_EXPORT_ENABLED, DEFAULT_AUTO_EXPORT_ENABLED))

    @property
    def auto_export_delay_hours(self) -> float:
        return float(
            self.options.get(CONF_AUTO_EXPORT_DELAY_HOURS, DEFAULT_AUTO_EXPORT_DELAY_HOURS)
        )

    @property
    def arrival_margin_minutes(self) -> int:
        return self._arrival_margin_minutes

    @property
    def departure_margin_minutes(self) -> int:
        return self._departure_margin_minutes

    @property
    def daily_net_target(self) -> float:
        return round(self.workday_hours - self.lunch_deduction, 2)

    @property
    def planned_end(self) -> datetime | None:
        if self.arrival is None:
            return None
        hours = self.workday_hours
        if self.lunch_status == LUNCH_NO:
            hours -= self.lunch_deduction
        return self.arrival + timedelta(hours=hours)

    # ------------------------------------------------------------------
    # Initialization / shutdown
    # ------------------------------------------------------------------
    async def async_initialize(self) -> None:
        """Load storage, restore today if same date, wire up listeners."""
        await self._async_load()

        today = dt_util.now().date()

        # Restore in-memory today state if date matches saved today
        # (today state is stored separately in the "today" key of storage)
        # Already done in _async_load() — _today_date, arrival etc. are set there.

        _LOGGER.info(
            "Worktime: tracking person='%s', work_zone='%s'",
            self.person_entity,
            self.work_zone,
        )

        # Zone tracking
        self._unsub.append(
            async_track_state_change_event(
                self.hass, [self.person_entity], self._handle_person_state_change
            )
        )

        # Notification action listener
        self._unsub.append(
            self.hass.bus.async_listen(
                EVENT_NOTIFICATION_ACTION, self._handle_notification_action
            )
        )

        # Lunch notification at configured time
        lt = self.lunch_time_obj
        self._unsub.append(
            async_track_time_change(
                self.hass,
                self._handle_lunch_time,
                hour=lt.hour,
                minute=lt.minute,
                second=lt.second,
            )
        )

        # Daily rollover at 03:00
        self._unsub.append(
            async_track_time_change(
                self.hass, self._handle_rollover, hour=3, minute=0, second=0
            )
        )

        # Friday timereport reminder at 16:00
        self._unsub.append(
            async_track_time_change(
                self.hass, self._handle_timereport_time, hour=16, minute=0, second=0
            )
        )

        # Morning reminder — checked every minute so options changes apply
        # without reload. The handler short-circuits when disabled.
        mr = self.morning_reminder_time_obj
        self._unsub.append(
            async_track_time_change(
                self.hass,
                self._handle_morning_reminder_time,
                hour=mr.hour,
                minute=mr.minute,
                second=0,
            )
        )

        # Initial zone check
        state = self.hass.states.get(self.person_entity)
        if (
            state
            and self._is_at_work(state.state)
            and self.arrival is None
        ):
            await self.async_register_arrival(manual=False)
        elif self.arrival is not None and self._departure is None:
            # Restored mid-day from storage — re-arm the forgot-departure
            # check so an HA restart doesn't drop the reminder.
            self._schedule_forgot_departure_check()

        self.async_set_updated_data(self.snapshot())

    async def async_shutdown(self) -> None:
        """Cancel all subscriptions."""
        for unsub in self._unsub:
            try:
                unsub()
            except Exception:  # pylint: disable=broad-except
                pass
        self._unsub.clear()
        if self._unsub_auto_export is not None:
            self._unsub_auto_export()
            self._unsub_auto_export = None
        if self._unsub_forgot_departure is not None:
            self._unsub_forgot_departure()
            self._unsub_forgot_departure = None
        if self._unsub_zone_exit is not None:
            self._unsub_zone_exit()
            self._unsub_zone_exit = None

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    async def _handle_person_state_change(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        if new_state is None:
            return

        was_at_work = bool(old_state and self._is_at_work(old_state.state))
        is_at_work = self._is_at_work(new_state.state)

        if not was_at_work and is_at_work:
            # Re-entered the zone before the grace window expired — drop
            # the pending exit so a brief Hemköp-and-back doesn't count.
            if self._unsub_zone_exit is not None:
                self._unsub_zone_exit()
                self._unsub_zone_exit = None
                _LOGGER.info("Worktime: re-entered work zone within grace — exit cancelled")
            _LOGGER.info("Worktime: arrived at work zone")
            # async_register_arrival keeps the first-of-the-day timestamp
            # untouched — it only sets arrival when none is registered yet.
            await self.async_register_arrival(manual=False)
        elif was_at_work and not is_at_work:
            # Debounce: brief absences (GPS jitter, errand next door) get
            # swallowed by the grace window. Only commit to auto-departure
            # if the user is still out after grace_minutes have passed.
            self._arm_zone_exit_check()

    def _arm_zone_exit_check(self) -> None:
        """Schedule the deferred zone-exit handler, replacing any pending
        one. With grace = 0 we run the check immediately to preserve the
        old behaviour."""
        if self._unsub_zone_exit is not None:
            self._unsub_zone_exit()
            self._unsub_zone_exit = None
        grace = self.zone_exit_grace_minutes
        if grace <= 0:
            self.hass.async_create_task(self._evaluate_zone_exit())
            return
        when = dt_util.now() + timedelta(minutes=grace)
        self._unsub_zone_exit = async_track_point_in_time(
            self.hass, self._handle_zone_exit_grace, when
        )
        _LOGGER.info("Worktime: zone exit — checking again at %s", when.isoformat())

    async def _handle_zone_exit_grace(self, _now: datetime) -> None:
        self._unsub_zone_exit = None
        await self._evaluate_zone_exit()

    async def _evaluate_zone_exit(self) -> None:
        """Run after the grace window elapses. If the user is still out
        of the zone and the auto-departure conditions are met, commit
        the departure now."""
        state = self.hass.states.get(self.person_entity)
        if state and self._is_at_work(state.state):
            # Already back at work — silently ignore (avoid log spam).
            return
        if not self._auto_departure_enabled:
            _LOGGER.info("Worktime: left zone — no auto-departure (disabled)")
            return
        if self.arrival is None or self._departure is not None:
            return
        now = dt_util.now()
        if now.time() < self.auto_departure_time_obj:
            _LOGGER.info("Worktime: left zone — no auto-departure (too early)")
            return
        _LOGGER.info(
            "Worktime: left zone after %s — auto-departure",
            self.auto_departure_time_obj,
        )
        await self.async_register_departure(manual=False)

    async def _handle_lunch_time(self, now: datetime) -> None:
        if self.arrival is None or self._departure is not None:
            return
        if self.lunch_status != LUNCH_UNKNOWN:
            return
        if self._lunch_notified:
            return
        await self._async_send_lunch_notification()

    async def _handle_rollover(self, now: datetime) -> None:
        """03:00 daily housekeeping — finalize previous day."""
        today = dt_util.now().date()
        if self._today_date is not None and self._today_date < today:
            # We have state from a previous date
            if self.arrival is not None and self._departure is None:
                _LOGGER.warning(
                    "Worktime: rollover — punch_out_missing for %s", self._today_date
                )
                await self._finalize_today(punch_out_missing=True)
        self._reset_today_state()
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    async def _handle_timereport_time(self, now: datetime) -> None:
        if now.weekday() != 4:  # Friday
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
                        "tag": self._scoped(NOTIFICATION_TAG_TIMEREPORT),
                        "actions": [
                            {"action": self._scoped(ACTION_TIMEREPORT_YES), "title": "Yes, done"},
                            {"action": self._scoped(ACTION_TIMEREPORT_NO), "title": "Not yet"},
                        ],
                    },
                },
                blocking=False,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: timereport notification failed: %s", exc)

    async def _handle_morning_reminder_time(self, now: datetime) -> None:
        """Send the morning reminder if the user hasn't arrived and today
        isn't already accounted for as sick / off / flex / home."""
        if not self.morning_reminder_enabled:
            return
        if self._morning_notified:
            return
        if self.arrival is not None:
            return
        today_iso = now.date().isoformat()
        if any(e.get("date") == today_iso for e in self.leave_records):
            # Already marked as a leave day — don't nag
            return
        svc = self.notify_service
        if not svc:
            return
        self._morning_notified = True
        try:
            await self.hass.services.async_call(
                "notify",
                svc,
                {
                    "title": "Worktime",
                    "message": "Good morning — how is today shaping up?",
                    "data": {
                        "tag": self._scoped(NOTIFICATION_TAG_MORNING),
                        "actions": [
                            {"action": self._scoped(ACTION_MORNING_ARRIVE), "title": "Clock in now"},
                            {"action": self._scoped(ACTION_MORNING_HOME), "title": "Working from home"},
                            {"action": self._scoped(ACTION_MORNING_SICK), "title": "Sick today"},
                        ],
                    },
                },
                blocking=False,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: morning reminder failed: %s", exc)

    def _schedule_forgot_departure_check(self) -> None:
        """Schedule a one-shot check at planned_end + offset minutes.
        Cancels any existing pending check first."""
        if self._unsub_forgot_departure is not None:
            self._unsub_forgot_departure()
            self._unsub_forgot_departure = None
        if not self.forgot_departure_enabled:
            return
        if self.arrival is None or self._departure is not None:
            return
        pe = self.planned_end
        if pe is None:
            return
        when = pe + timedelta(minutes=self.forgot_departure_offset_minutes)
        if when <= dt_util.now():
            # Already past — fire shortly so a freshly started HA notices
            when = dt_util.now() + timedelta(seconds=15)
        self._unsub_forgot_departure = async_track_point_in_time(
            self.hass, self._handle_forgot_departure, when
        )
        _LOGGER.debug("Worktime: scheduled forgot-departure check at %s", when.isoformat())

    async def _handle_forgot_departure(self, _now: datetime) -> None:
        self._unsub_forgot_departure = None
        if not self.forgot_departure_enabled:
            return
        if self._forgot_departure_notified:
            return
        if self.arrival is None or self._departure is not None:
            return
        svc = self.notify_service
        if not svc:
            return
        self._forgot_departure_notified = True
        try:
            await self.hass.services.async_call(
                "notify",
                svc,
                {
                    "title": "Worktime",
                    "message": "Still at work? Don't forget to clock out.",
                    "data": {
                        "tag": self._scoped(NOTIFICATION_TAG_DEPARTURE),
                        "actions": [
                            {"action": self._scoped(ACTION_DEPARTURE_NOW), "title": "Clock out now"},
                        ],
                    },
                },
                blocking=False,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: forgot-departure notification failed: %s", exc)

    async def _handle_notification_action(self, event: Event) -> None:
        """Notification actions are emitted as a single global event;
        every coordinator receives every action. Each coordinator only
        responds to actions whose id ends with its own instance slug,
        so 'Otto's lunch yes' doesn't also mark Ellen as having eaten."""
        action = event.data.get("action") or ""
        if self._matches_my_action(action, ACTION_LUNCH_YES):
            await self.async_set_lunch(LUNCH_YES)
        elif self._matches_my_action(action, ACTION_LUNCH_NO):
            await self.async_set_lunch(LUNCH_NO)
        elif self._matches_my_action(action, ACTION_TIMEREPORT_YES):
            await self._async_append_to_sheet(source="notification")
        elif self._matches_my_action(action, ACTION_MORNING_ARRIVE):
            await self.async_register_arrival(manual=True)
        elif self._matches_my_action(action, ACTION_MORNING_HOME):
            await self.async_edit_day(
                target_date=dt_util.now().date(),
                day_type=DAY_TYPE_HOME,
            )
        elif self._matches_my_action(action, ACTION_MORNING_SICK):
            await self.async_edit_day(
                target_date=dt_util.now().date(),
                day_type=DAY_TYPE_SICK,
            )
        elif self._matches_my_action(action, ACTION_DEPARTURE_NOW):
            await self.async_register_departure(manual=True)

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    async def async_register_arrival(self, manual: bool = False) -> None:
        """Register arrival. Skipped if already registered (unless manual)."""
        if self.arrival is not None and not manual:
            return
        now = dt_util.now()
        stamp = now
        if not manual and self._arrival_margin_minutes > 0:
            stamp = now + timedelta(minutes=self._arrival_margin_minutes)
            _LOGGER.info(
                "Worktime: applying arrival margin +%d min (%s → %s)",
                self._arrival_margin_minutes,
                now.isoformat(),
                stamp.isoformat(),
            )
        self.arrival = stamp
        self._departure = None
        self._lunch_notified = False
        self.lunch_status = LUNCH_UNKNOWN
        self._today_date = now.date()
        _LOGGER.info("Worktime: arrival registered at %s", self.arrival.isoformat())
        await self._async_save()
        self.async_set_updated_data(self.snapshot())
        self._schedule_forgot_departure_check()

    async def async_register_departure(self, manual: bool = False) -> None:
        """Register departure, calculate hours, save to history."""
        if self.arrival is None:
            _LOGGER.debug("Worktime: departure ignored — no arrival registered")
            return
        now = dt_util.now()
        stamp = now
        if not manual and self._departure_margin_minutes > 0:
            stamp = now - timedelta(minutes=self._departure_margin_minutes)
            # Never set departure before arrival
            if stamp < self.arrival:
                stamp = self.arrival
            _LOGGER.info(
                "Worktime: applying departure margin -%d min (%s → %s)",
                self._departure_margin_minutes,
                now.isoformat(),
                stamp.isoformat(),
            )
        self._departure = stamp
        if self._unsub_forgot_departure is not None:
            self._unsub_forgot_departure()
            self._unsub_forgot_departure = None

        # Resolve lunch at departure time using early-departure guard
        if self.lunch_status == LUNCH_UNKNOWN:
            self.lunch_status = LUNCH_YES if self.auto_lunch_default else LUNCH_NO

        await self._finalize_today(punch_out_missing=False)
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

        # Schedule auto-export
        if self.auto_export_enabled and self.sheets_entry_id:
            if self._unsub_auto_export is not None:
                self._unsub_auto_export()
            delay = self.auto_export_delay_hours * 3600
            self._unsub_auto_export = async_call_later(
                self.hass, delay, self._async_auto_export_callback
            )
            _LOGGER.info("Worktime: auto-export scheduled in %.1fh", self.auto_export_delay_hours)

    @callback
    def _async_auto_export_callback(self, _now: datetime) -> None:
        self._unsub_auto_export = None
        self.hass.async_create_task(self._async_append_to_sheet())

    async def async_set_lunch(self, status: str) -> None:
        if status not in (LUNCH_YES, LUNCH_NO):
            return
        self.lunch_status = status
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    async def async_reset_today(self) -> None:
        self._reset_today_state()
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    async def async_export_today(self) -> None:
        """Re-send today's row to Sheets."""
        if self.arrival is None:
            _LOGGER.info("Worktime: nothing to export for today")
            return
        await self._async_append_to_sheet(source="manual")

    async def async_edit_day(
        self,
        target_date: date,
        arrival: str | None = None,
        departure: str | None = None,
        lunch: str | None = None,
        day_type: str | None = None,
        hours: float | None = None,
    ) -> None:
        """Edit or create a day entry.

        If day_type == 'sick': add/replace in leave_records.
        Otherwise: edit/create in history.
        """
        today = dt_util.now().date()
        target_iso = target_date.isoformat()

        def _parse_hhmm(t: str, ref_date: date) -> datetime:
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
            local = datetime(ref_date.year, ref_date.month, ref_date.day, h, m)
            return dt_util.as_utc(dt_util.as_local(local))

        if day_type in (DAY_TYPE_SICK, DAY_TYPE_OFF, DAY_TYPE_FLEX, DAY_TYPE_HOME):
            if day_type in (DAY_TYPE_SICK, DAY_TYPE_HOME):
                # Sick / home default to a full net workday's worth of
                # credit — they represent a whole day away from the
                # office. Override with the hours argument for partial
                # days (e.g. half-day sick: pass hours=4).
                default_hours = float(
                    self.options.get(CONF_WORKDAY_HOURS, DEFAULT_WORKDAY_HOURS)
                ) - self.lunch_deduction
                leave_hours = hours if hours is not None else default_hours
            elif day_type == DAY_TYPE_FLEX:
                # Flex is an explicit credit/debit — never default to a
                # whole workday. If the caller didn't pass hours we
                # record 0 so the user has to enter what they want.
                leave_hours = hours if hours is not None else 0.0
            else:
                # Off day — counts 0 hours (vacation, day off)
                leave_hours = hours if hours is not None else 0.0
            leave_entry: dict[str, Any] = {
                "date": target_iso,
                "type": day_type,
                "hours": round(leave_hours, 2),
                "edited": True,
            }
            replaced = False
            for i, e in enumerate(self.leave_records):
                if e.get("date") == target_iso:
                    self.leave_records[i] = leave_entry
                    replaced = True
                    break
            if not replaced:
                self.leave_records.append(leave_entry)
            # Remove from history if it was previously logged there
            self.history = [e for e in self.history if e.get("date") != target_iso]
            await self._async_save()
            self.async_set_updated_data(self.snapshot())
            _LOGGER.info("Worktime: %s day set for %s (%.2fh)", day_type, target_iso, leave_hours)
            await self._async_append_to_sheet(entry=leave_entry, source="edit")
            return

        # Normal day edit
        # Find or create history entry
        entry: dict[str, Any] | None = None
        for e in self.history:
            if e.get("date") == target_iso:
                entry = e
                break
        if entry is None:
            entry = {
                "date": target_iso,
                "arrival": None,
                "departure": None,
                "lunch": LUNCH_UNKNOWN,
                "lunch_deduction": self.lunch_deduction,
                "hours": 0.0,
                "type": DAY_TYPE_NORMAL,
                "punch_out_missing": False,
                "edited": False,
            }
            self.history.append(entry)

        if arrival:
            entry["arrival"] = _parse_hhmm(arrival, target_date).isoformat()
        if departure:
            entry["departure"] = _parse_hhmm(departure, target_date).isoformat()
        if lunch:
            entry["lunch"] = lunch

        # Recalculate hours. An explicit hours= argument wins over the
        # arrival→departure calculation — that's how the user overrides
        # a day's total (e.g. trim accidental overtime, or set a half-
        # day worked manually).
        if hours is not None:
            entry["hours"] = max(0.0, round(float(hours), 2))
            entry["lunch_deduction"] = (
                self.lunch_deduction
                if self._should_deduct_lunch_for_entry(entry) else 0.0
            )
        elif entry.get("arrival") and entry.get("departure"):
            arr = datetime.fromisoformat(entry["arrival"])
            dep = datetime.fromisoformat(entry["departure"])
            raw_hours = (dep - arr).total_seconds() / 3600.0
            deduction = self.lunch_deduction if self._should_deduct_lunch_for_entry(entry) else 0.0
            entry["lunch_deduction"] = deduction
            entry["hours"] = max(0.0, round(raw_hours - deduction, 2))

        entry["edited"] = True

        await self._async_save()

        # If editing today, sync in-memory state
        if target_date == today:
            if entry.get("arrival"):
                self.arrival = datetime.fromisoformat(entry["arrival"])
            if entry.get("departure"):
                self._departure = datetime.fromisoformat(entry["departure"])
            if lunch:
                self.lunch_status = lunch
            await self._async_save()

        self.async_set_updated_data(self.snapshot())
        _LOGGER.info("Worktime: edited day %s → %s", target_iso, entry)

    async def async_clear_day(self, target_date: date) -> None:
        """Wipe a day completely — removes any history + leave_records
        entries for the date, and if it's today also clears the live
        arrival / departure / lunch state so you can start tracking from
        scratch. The Sheets row is left alone (manual cleanup there)."""
        target_iso = target_date.isoformat()
        before_history = len(self.history)
        before_leave = len(self.leave_records)
        self.history = [
            e for e in self.history if e.get("date") != target_iso
        ]
        self.leave_records = [
            e for e in self.leave_records if e.get("date") != target_iso
        ]
        removed = (before_history - len(self.history)) + (
            before_leave - len(self.leave_records)
        )

        if target_date == dt_util.now().date():
            self._reset_today_state()

        # Drop any cached export fingerprint for this date so a subsequent
        # export_all will re-emit cleanly if the user logs the day again.
        self.sheets_sync.pop(target_iso, None)

        await self._async_save()
        self.async_set_updated_data(self.snapshot())
        _LOGGER.info(
            "Worktime: cleared %s (%d entries removed)", target_iso, removed
        )
        await self._async_append_to_sheet(entry=entry, source="edit")

    async def async_set_auto_departure_enabled(self, enabled: bool) -> None:
        self._auto_departure_enabled = enabled
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    async def async_set_arrival_margin_minutes(self, minutes: int) -> None:
        self._arrival_margin_minutes = max(0, min(MAX_MARGIN_MINUTES, int(minutes)))
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    async def async_set_departure_margin_minutes(self, minutes: int) -> None:
        self._departure_margin_minutes = max(0, min(MAX_MARGIN_MINUTES, int(minutes)))
        await self._async_save()
        self.async_set_updated_data(self.snapshot())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _reset_today_state(self) -> None:
        self.arrival = None
        self._departure = None
        self.lunch_status = LUNCH_UNKNOWN
        self._lunch_notified = False
        self._morning_notified = False
        self._forgot_departure_notified = False
        self._today_date = None
        if self._unsub_forgot_departure is not None:
            self._unsub_forgot_departure()
            self._unsub_forgot_departure = None
        if self._unsub_zone_exit is not None:
            self._unsub_zone_exit()
            self._unsub_zone_exit = None

    def _should_deduct_lunch(self) -> bool:
        """For today's live state. Apply early-departure guard."""
        if self.lunch_status == LUNCH_NO:
            return False
        dep_time = (self._departure or dt_util.now()).astimezone(
            dt_util.DEFAULT_TIME_ZONE
        ).time()
        lunch_time = self.lunch_time_obj
        if dep_time < lunch_time:
            # Departed before lunch time — never deduct regardless of setting
            return False
        if self.lunch_status == LUNCH_YES:
            return True
        # lunch == unknown with auto_lunch_default
        return self.auto_lunch_default

    def _should_deduct_lunch_for_entry(self, entry: dict[str, Any]) -> bool:
        """For a history/edit entry. Apply early-departure guard."""
        lunch = entry.get("lunch", LUNCH_UNKNOWN)
        if lunch == LUNCH_NO:
            return False
        dep_iso = entry.get("departure")
        if dep_iso:
            try:
                dep_local = dt_util.as_local(datetime.fromisoformat(dep_iso))
                if dep_local.time() < self.lunch_time_obj:
                    return False
            except Exception:  # pylint: disable=broad-except
                pass
        if lunch == LUNCH_YES:
            return True
        return self.auto_lunch_default

    async def _finalize_today(self, punch_out_missing: bool = False) -> None:
        """Build a history entry from today's state and append to self.history."""
        if self.arrival is None:
            return
        target_iso = (self._today_date or dt_util.now().date()).isoformat()
        hours = self.hours_worked_today()
        deduction = self.lunch_deduction if self._should_deduct_lunch() else 0.0

        entry: dict[str, Any] = {
            "date": target_iso,
            "arrival": self.arrival.isoformat(),
            "departure": self._departure.isoformat() if self._departure else None,
            "lunch": self.lunch_status,
            "lunch_deduction": deduction,
            "hours": hours,
            "type": DAY_TYPE_NORMAL,
            "punch_out_missing": punch_out_missing,
            "edited": False,
        }

        replaced = False
        for i, e in enumerate(self.history):
            if e.get("date") == target_iso:
                # Preserve edited flag if already edited
                entry["edited"] = e.get("edited", False)
                self.history[i] = entry
                replaced = True
                break
        if not replaced:
            self.history.append(entry)

        # Trim to max 180 entries
        if len(self.history) > 180:
            self.history = self.history[-180:]

    # ------------------------------------------------------------------
    # Computed values
    # ------------------------------------------------------------------
    def hours_worked_today(self) -> float:
        if self.arrival is None:
            return 0.0
        end = self._departure or dt_util.now()
        raw = (end - self.arrival).total_seconds() / 3600.0
        deduction = self.lunch_deduction if self._should_deduct_lunch() else 0.0
        return max(0.0, round(raw - deduction, 2))

    def overtime_today(self) -> float:
        if self.arrival is None:
            return 0.0
        return round(self.hours_worked_today() - self.daily_net_target, 2)

    def time_remaining_seconds(self) -> int:
        pe = self.planned_end
        if self.arrival is None or pe is None:
            return 0
        if self._departure is not None:
            return 0
        return int((pe - dt_util.now()).total_seconds())

    def status(self) -> str:
        if self.arrival is None:
            return STATUS_OFF_DUTY
        if self._departure is not None:
            return STATUS_DONE
        pe = self.planned_end
        if pe and dt_util.now() >= pe:
            return STATUS_OVERTIME
        return STATUS_AT_WORK

    def _all_credited_days(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Combine history + leave_records in [start_date, end_date]."""
        result = []
        for e in self.history:
            try:
                d = date.fromisoformat(e["date"])
            except Exception:  # pylint: disable=broad-except
                continue
            if start_date <= d <= end_date:
                result.append(e)
        for e in self.leave_records:
            try:
                d = date.fromisoformat(e["date"])
            except Exception:  # pylint: disable=broad-except
                continue
            if start_date <= d <= end_date:
                result.append(e)
        return result

    def hours_worked_in_week(self, weeks_back: int = 0) -> float:
        today = dt_util.now().date()
        target = today - timedelta(weeks=weeks_back)
        year, week, _ = target.isocalendar()
        monday = target - timedelta(days=target.weekday())
        sunday = monday + timedelta(days=6)
        total = 0.0
        for entry in self._all_credited_days(monday, sunday):
            try:
                d = date.fromisoformat(entry["date"])
            except Exception:  # pylint: disable=broad-except
                continue
            dy, dw, _ = d.isocalendar()
            if dy == year and dw == week:
                total += float(entry.get("hours", 0.0))
        # Add live today hours if this week and not finalized
        if weeks_back == 0 and today.isocalendar()[:2] == (year, week):
            already_done = any(
                e.get("date") == today.isoformat() and e.get("departure")
                for e in self.history
            )
            if not already_done and self.arrival is not None:
                total += self.hours_worked_today()
        return round(total, 2)

    def hours_worked_last_week(self) -> float:
        return self.hours_worked_in_week(weeks_back=1)

    def hours_worked_in_month(self, year: int, month: int) -> float:
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        total = 0.0
        for entry in self._all_credited_days(start, end):
            total += float(entry.get("hours", 0.0))
        today = dt_util.now().date()
        if today.year == year and today.month == month:
            already_done = any(
                e.get("date") == today.isoformat() and e.get("departure")
                for e in self.history
            )
            if not already_done and self.arrival is not None:
                total += self.hours_worked_today()
        return round(total, 2)

    def overtime_this_week(self) -> float:
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
                for e in self._all_credited_days(monday, today)
            )
            if not has_work and d == today and self.arrival is not None:
                has_work = True
            if has_work:
                days_with_work += 1
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_in_week() - expected, 2)

    def overtime_last_week(self) -> float:
        today = dt_util.now().date()
        last_week_target = today - timedelta(weeks=1)
        monday = last_week_target - timedelta(days=last_week_target.weekday())
        friday = monday + timedelta(days=4)
        days_with_work = 0
        for offset in range(5):
            d = monday + timedelta(days=offset)
            d_iso = d.isoformat()
            if any(
                e.get("date") == d_iso and float(e.get("hours", 0)) > 0
                for e in self._all_credited_days(monday, friday)
            ):
                days_with_work += 1
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_last_week() - expected, 2)

    def overtime_this_month(self) -> float:
        today = dt_util.now().date()
        from calendar import monthrange
        last_day = monthrange(today.year, today.month)[1]
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, last_day)
        days_with_work = 0
        for entry in self._all_credited_days(start, today):
            if float(entry.get("hours", 0)) > 0:
                days_with_work += 1
        # Ensure today counted if in-progress
        already_done = any(
            e.get("date") == today.isoformat() and e.get("departure")
            for e in self.history
        )
        if not already_done and self.arrival is not None:
            days_with_work += 1
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_in_month(today.year, today.month) - expected, 2)

    def overtime_last_month(self) -> float:
        today = dt_util.now().date()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        days_with_work = sum(
            1
            for e in self._all_credited_days(start, end)
            if float(e.get("hours", 0)) > 0
        )
        expected = days_with_work * self.daily_net_target
        return round(self.hours_worked_in_month(year, month) - expected, 2)

    def month_name(self, months_back: int = 0) -> str:
        today = dt_util.now().date()
        month = today.month - months_back
        year = today.year
        while month < 1:
            month += 12
            year -= 1
        return date(year, month, 1).strftime("%B %Y")

    def week_breakdown(self, weeks_back: int = 0) -> list[dict[str, Any]]:
        today = dt_util.now().date()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_back)
        result = []
        for offset in range(5):
            d = monday + timedelta(days=offset)
            d_iso = d.isoformat()

            # Search history and leave_records
            entry: dict[str, Any] | None = None
            for e in self.history:
                if e.get("date") == d_iso:
                    entry = e
                    break
            if entry is None:
                for e in self.leave_records:
                    if e.get("date") == d_iso:
                        entry = e
                        break

            # Live today
            if entry is None and d == today and self.arrival is not None:
                entry = {
                    "date": d_iso,
                    "arrival": self.arrival.isoformat(),
                    "departure": self._departure.isoformat() if self._departure else None,
                    "lunch": self.lunch_status,
                    "hours": self.hours_worked_today(),
                    "type": DAY_TYPE_NORMAL,
                }

            def _p(iso: str | None) -> str:
                if not iso:
                    return "—"
                try:
                    return dt_util.as_local(datetime.fromisoformat(iso)).strftime("%H:%M")
                except Exception:  # pylint: disable=broad-except
                    return "—"

            if entry:
                hours = float(entry.get("hours", 0.0))
                day_type = entry.get("type", DAY_TYPE_NORMAL)
                dep_iso = entry.get("departure") or (
                    self.planned_end.isoformat() if d == today and self.planned_end else None
                )
                result.append({
                    "date": d_iso,
                    "weekday": _SHORT_DAYS[d.weekday()],
                    "arrival": _p(entry.get("arrival")),
                    "departure": _p(dep_iso),
                    "lunch": entry.get("lunch", "—"),
                    "hours": round(hours, 2),
                    "human_readable": _hours_to_human(hours),
                    "type": day_type,
                    "punch_out_missing": entry.get("punch_out_missing", False),
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
                    "type": "none",
                    "punch_out_missing": False,
                })
        return result

    def recent_days(self, count: int = 60) -> list[dict[str, Any]]:
        """Return last `count` days that have data, newest first."""
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
            if entry is None:
                for e in self.leave_records:
                    if e.get("date") == d_iso:
                        entry = e
                        break

            if entry is None and d == today and self.arrival is not None:
                entry = {
                    "date": d_iso,
                    "arrival": self.arrival.isoformat(),
                    "departure": self._departure.isoformat() if self._departure else None,
                    "lunch": self.lunch_status,
                    "hours": self.hours_worked_today(),
                    "type": DAY_TYPE_NORMAL,
                }

            if not entry:
                continue

            def _p(iso: str | None) -> str:
                if not iso:
                    return "—"
                try:
                    return dt_util.as_local(datetime.fromisoformat(iso)).strftime("%H:%M")
                except Exception:  # pylint: disable=broad-except
                    return "—"

            hours = float(entry.get("hours", 0.0))
            dep_iso = entry.get("departure") or (
                self.planned_end.isoformat() if d == today and self.planned_end else None
            )
            result.append({
                "date": d_iso,
                "weekday": _SHORT_DAYS[d.weekday()],
                "arrival": _p(entry.get("arrival")),
                "departure": _p(dep_iso),
                "lunch": entry.get("lunch", "—"),
                "hours": round(hours, 2),
                "human_readable": _hours_to_human(hours),
                "type": entry.get("type", DAY_TYPE_NORMAL),
                "punch_out_missing": entry.get("punch_out_missing", False),
            })
        return result

    def snapshot(self) -> dict[str, Any]:
        return {
            "arrival": self.arrival,
            "planned_end": self.planned_end,
            "departure": self._departure,
            "lunch": self.lunch_status,
            "hours_today": self.hours_worked_today(),
            "hours_week": self.hours_worked_in_week(),
            "overtime_today": self.overtime_today(),
            "overtime_week": self.overtime_this_week(),
            "remaining_seconds": self.time_remaining_seconds(),
            "status": self.status(),
            "history": self.history,
            "leave_records": self.leave_records,
            "weekly_target": self.weekly_target,
            "workday_hours": self.workday_hours,
            "daily_net_target": self.daily_net_target,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _is_oldest_entry(self) -> bool:
        """Whether this entry is the earliest active config entry of the
        domain. Used to decide which entry inherits the pre-2.5.2 single-
        file storage."""
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if not entries:
            return False
        return entries[0].entry_id == self.entry.entry_id

    async def _async_load(self) -> None:
        """Load storage, migrate v1 → v2 if needed, and (one-time)
        migrate the legacy shared file into this entry's per-entry file
        if this is the oldest config entry."""
        raw = await self._store.async_load()
        if not raw and self._is_oldest_entry():
            legacy = await self._legacy_store.async_load()
            if legacy:
                _LOGGER.info(
                    "Worktime: migrating legacy shared storage into entry %s",
                    self.entry.entry_id,
                )
                raw = legacy
                # Persist into the per-entry file so we never re-migrate.
                await self._store.async_save(legacy)
                # Drop the shared file so any newly-added entry starts
                # genuinely empty instead of inheriting the same data.
                await self._legacy_store.async_remove()
        raw = raw or {}
        schema_version = raw.get("schema_version", 1)

        if schema_version == 1:
            raw = self._migrate_v1_to_v2(raw)

        self.history = raw.get("history", [])
        self.leave_records = raw.get("leave_records", [])
        self.sheets_sync = raw.get("sheets_sync", {}) or {}

        if len(self.history) > 180:
            self.history = self.history[-180:]

        if "auto_departure_enabled" in raw:
            self._auto_departure_enabled = bool(raw["auto_departure_enabled"])
        else:
            self._auto_departure_enabled = bool(
                self.options.get(CONF_AUTO_DEPARTURE_ENABLED, DEFAULT_AUTO_DEPARTURE_ENABLED)
            )

        self._arrival_margin_minutes = max(
            0,
            min(
                MAX_MARGIN_MINUTES,
                int(raw.get("arrival_margin_minutes", DEFAULT_ARRIVAL_MARGIN_MINUTES)),
            ),
        )
        self._departure_margin_minutes = max(
            0,
            min(
                MAX_MARGIN_MINUTES,
                int(raw.get("departure_margin_minutes", DEFAULT_DEPARTURE_MARGIN_MINUTES)),
            ),
        )

        # Restore today's in-memory state
        today_data = raw.get("today")
        if today_data and today_data.get("date"):
            try:
                saved_date = date.fromisoformat(today_data["date"])
                now_date = dt_util.now().date()
                if saved_date == now_date:
                    arrival_iso = today_data.get("arrival")
                    self.arrival = datetime.fromisoformat(arrival_iso) if arrival_iso else None
                    dep_iso = today_data.get("departure")
                    self._departure = datetime.fromisoformat(dep_iso) if dep_iso else None
                    self.lunch_status = today_data.get("lunch", LUNCH_UNKNOWN)
                    self._lunch_notified = bool(today_data.get("lunch_notified", False))
                    self._today_date = saved_date
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("Worktime: failed to restore today state: %s", exc)

    def _migrate_v1_to_v2(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Migrate v1 storage (single flat history list) to v2 format."""
        _LOGGER.info("Worktime: migrating storage from v1 to v2")
        old_history: list[dict[str, Any]] = raw.get("history", [])
        new_history: list[dict[str, Any]] = []
        new_leave: list[dict[str, Any]] = []

        for entry in old_history:
            if entry.get("type") == DAY_TYPE_SICK:
                # Move sick entries to leave_records
                new_leave.append({
                    "date": entry.get("date", ""),
                    "type": DAY_TYPE_SICK,
                    "hours": float(entry.get("hours", 8.0)),
                    "edited": entry.get("edited", False),
                })
            else:
                # Add missing v2 fields
                if "lunch_deduction" not in entry:
                    entry["lunch_deduction"] = self.lunch_deduction
                if "punch_out_missing" not in entry:
                    entry["punch_out_missing"] = False
                if "type" not in entry:
                    entry["type"] = DAY_TYPE_NORMAL
                if "edited" not in entry:
                    entry["edited"] = False
                new_history.append(entry)

        return {
            "schema_version": 2,
            "auto_departure_enabled": raw.get("auto_departure_enabled", False),
            "history": new_history,
            "leave_records": new_leave,
            "today": raw.get("today"),
        }

    async def _async_save(self) -> None:
        """Persist full state to storage."""
        today_blob: dict[str, Any] | None = None
        if self.arrival is not None:
            today_date = self._today_date or dt_util.now().date()
            today_blob = {
                "date": today_date.isoformat(),
                "arrival": self.arrival.isoformat(),
                "departure": self._departure.isoformat() if self._departure else None,
                "lunch": self.lunch_status,
                "lunch_notified": self._lunch_notified,
            }

        await self._store.async_save({
            "schema_version": STORAGE_VERSION,
            "auto_departure_enabled": self._auto_departure_enabled,
            "arrival_margin_minutes": self._arrival_margin_minutes,
            "departure_margin_minutes": self._departure_margin_minutes,
            "today": today_blob,
            "history": self.history,
            "leave_records": self.leave_records,
            "sheets_sync": self.sheets_sync,
        })

    # ------------------------------------------------------------------
    # Google Sheets export
    # ------------------------------------------------------------------
    def _format_time(self, dt_obj: datetime | None) -> str:
        if not dt_obj:
            return ""
        return dt_util.as_local(dt_obj).strftime("%H:%M")

    def _build_sheet_row(
        self,
        entry: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str, str] | None:
        """Build a Sheets row dict + its content fingerprint + ISO date.

        Returns None if the entry can't be parsed. The fingerprint covers
        the user-visible fields so re-exports skip unchanged days.
        """
        if entry is None:
            target_date = self._today_date or dt_util.now().date()
            arrival = self.arrival
            departure = self._departure
            lunch = self.lunch_status
            hours = self.hours_worked_today()
            day_type = DAY_TYPE_NORMAL
            edited = False
            punch_out_missing = False
            planned = self.planned_end
        else:
            try:
                target_date = date.fromisoformat(entry["date"])
                arrival_iso = entry.get("arrival")
                arrival = datetime.fromisoformat(arrival_iso) if arrival_iso else None
                dep_iso = entry.get("departure")
                departure = datetime.fromisoformat(dep_iso) if dep_iso else None
                lunch = entry.get("lunch", LUNCH_UNKNOWN)
                hours = float(entry.get("hours", 0.0))
                day_type = entry.get("type", DAY_TYPE_NORMAL)
                edited = bool(entry.get("edited", False))
                punch_out_missing = bool(entry.get("punch_out_missing", False))
                if arrival:
                    hrs = self.workday_hours
                    if entry.get("lunch") == LUNCH_NO:
                        hrs -= self.lunch_deduction
                    planned = arrival + timedelta(hours=hrs)
                else:
                    planned = None
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("Worktime: failed to parse entry for Sheets: %s", exc)
                return None

        overtime = round(hours - self.daily_net_target, 2)
        iso = target_date.isoformat()

        row = {
            "Date": iso,
            "Weekday": _WEEKDAYS[target_date.weekday()],
            "Type": (
                "Sick" if day_type == DAY_TYPE_SICK
                else "Off" if day_type == DAY_TYPE_OFF
                else "Flex" if day_type == DAY_TYPE_FLEX
                else "Home" if day_type == DAY_TYPE_HOME
                else "Normal"
            ),
            "Arrival": self._format_time(arrival),
            "Planned end": self._format_time(planned),
            "Departure": self._format_time(departure),
            "Lunch": lunch,
            "Hours": round(hours, 4),
            "Hours (rounded)": f"{_round_quarter(hours):.2f}h",
            "Overtime": overtime,
            "Edited": "yes" if edited else "no",
            "Punch-out missing": "yes" if punch_out_missing else "no",
        }

        fp_payload = {
            "type": row["Type"],
            "arrival": row["Arrival"],
            "departure": row["Departure"],
            "lunch": row["Lunch"],
            "hours": row["Hours"],
            "edited": row["Edited"],
            "punch_out_missing": row["Punch-out missing"],
        }
        fp = hashlib.sha256(
            json.dumps(fp_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return row, fp, iso

    async def _async_send_row(
        self,
        row: dict[str, Any],
        iso: str,
        fp: str,
        source: str,
    ) -> bool:
        """Send a single prepared row, stamping Rev/Source/Updated at and
        updating sheets_sync. Returns True on success.

        Sheets integration is fully optional: if it isn't configured or
        installed we no-op silently."""
        entry_id = self.sheets_entry_id
        if not entry_id:
            return False
        if not self.hass.services.has_service("google_sheets", "append_sheet"):
            _LOGGER.warning("Worktime: google_sheets not installed — skipping export")
            return False

        prev = self.sheets_sync.get(iso, {})
        prev_rev = int(prev.get("rev", 0) or 0)
        prev_fp = prev.get("fp")
        rev = prev_rev + 1 if prev_fp is not None and prev_fp != fp else (prev_rev or 1)
        now_iso = dt_util.now().replace(microsecond=0).isoformat()

        row = {
            **row,
            "Rev": rev,
            "Source": source,
            "Updated at": now_iso,
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
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Worktime: Sheets append failed for %s: %s", iso, exc)
            return False

        self.sheets_sync[iso] = {"rev": rev, "fp": fp, "ts": now_iso}
        return True

    async def _async_append_to_sheet(
        self,
        entry: dict[str, Any] | None = None,
        source: str = "auto",
    ) -> None:
        """Append (or re-append) one day. Default source is 'auto' for
        the punch-out / edit flow; callers can override (e.g. 'today' for
        a manual export-today click)."""
        if not self.sheets_entry_id:
            return
        built = self._build_sheet_row(entry)
        if built is None:
            return
        row, fp, iso = built
        sent = await self._async_send_row(row, iso, fp, source)
        if sent:
            await self._async_save()
            _LOGGER.info("Worktime: appended %s (rev %d) to '%s'",
                         iso, self.sheets_sync[iso]["rev"], self.sheets_worksheet)

    async def async_export_all(
        self,
        since: date | None = None,
        force: bool = False,
    ) -> dict[str, int]:
        """Walk every locally-known day and push anything not yet in Sheets
        (or anything that has changed since last push). Returns a small
        summary dict. Sheets is optional — if it isn't configured this is
        a no-op."""
        if not self.sheets_entry_id:
            _LOGGER.info("Worktime: export_all — Sheets not configured, skipping")
            return {"sent": 0, "skipped": 0, "failed": 0, "total": 0}
        if not self.hass.services.has_service("google_sheets", "append_sheet"):
            _LOGGER.warning("Worktime: export_all — google_sheets not installed")
            return {"sent": 0, "skipped": 0, "failed": 0, "total": 0}

        # Combine all known days. History and leave_records are mutually
        # exclusive by date (see async_edit_day), but be defensive anyway.
        seen: set[str] = set()
        combined: list[dict[str, Any]] = []
        for e in self.history + self.leave_records:
            iso = e.get("date")
            if not iso or iso in seen:
                continue
            if since and iso < since.isoformat():
                continue
            seen.add(iso)
            combined.append(e)
        combined.sort(key=lambda e: e.get("date", ""))

        sent = skipped = failed = 0
        for e in combined:
            built = self._build_sheet_row(e)
            if built is None:
                failed += 1
                continue
            row, fp, iso = built
            prev_fp = self.sheets_sync.get(iso, {}).get("fp")
            if not force and prev_fp == fp:
                skipped += 1
                continue
            source = "export_all_force" if force else "export_all"
            ok = await self._async_send_row(row, iso, fp, source)
            if ok:
                sent += 1
            else:
                failed += 1

        if sent:
            await self._async_save()
        _LOGGER.info(
            "Worktime: export_all done — sent=%d skipped=%d failed=%d total=%d",
            sent, skipped, failed, len(combined),
        )
        return {"sent": sent, "skipped": skipped, "failed": failed, "total": len(combined)}

    async def _async_send_lunch_notification(self) -> None:
        svc = self.notify_service
        if not svc:
            _LOGGER.warning("Worktime: lunch time but no notify service configured")
            return
        try:
            await self.hass.services.async_call(
                "notify",
                svc,
                {
                    "title": "Lunch check",
                    "message": "Did you have lunch today?",
                    "data": {
                        "tag": self._scoped(NOTIFICATION_TAG),
                        "actions": [
                            {"action": self._scoped(ACTION_LUNCH_YES), "title": "Yes"},
                            {"action": self._scoped(ACTION_LUNCH_NO), "title": "No"},
                        ],
                    },
                },
                blocking=False,
            )
            self._lunch_notified = True
            await self._async_save()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Worktime: lunch notification failed: %s", exc)
