"""Constants for the Worktime Tracker integration."""
from __future__ import annotations

DOMAIN = "worktime_tracker"

# Configuration keys
# NOTE: Python constant renamed for clarity, but stored key strings kept for backward compat.
CONF_PERSON = "person_entity"               # was CONF_PERSON_ENTITY
CONF_WORK_ZONE = "work_zone"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_LUNCH_TIME = "lunch_time"
CONF_WORKDAY_HOURS = "workday_hours"
CONF_LUNCH_DEDUCTION = "lunch_deduction"
CONF_WEEKLY_TARGET = "weekly_target"
CONF_SHEETS_ENTRY_ID = "sheets_config_entry"  # was CONF_SHEETS_ENTRY (same stored key)
CONF_SHEETS_WORKSHEET = "sheets_worksheet"
CONF_AUTO_LUNCH_DEFAULT = "auto_lunch_default"
CONF_AUTO_DEPARTURE_ENABLED = "auto_departure_enabled"
CONF_AUTO_DEPARTURE_TIME = "auto_departure_time"
CONF_AUTO_EXPORT_ENABLED = "auto_export_enabled"
CONF_AUTO_EXPORT_DELAY_HOURS = "auto_export_delay_hours"
CONF_ARRIVAL_MARGIN_MINUTES = "arrival_margin_minutes"
CONF_DEPARTURE_MARGIN_MINUTES = "departure_margin_minutes"

# Defaults
DEFAULT_LUNCH_TIME = "13:00"
DEFAULT_WORKDAY_HOURS = 8.5  # Gross (includes lunch break)
DEFAULT_LUNCH_DEDUCTION = 0.5  # 30 minutes
DEFAULT_WEEKLY_TARGET = 40.0
DEFAULT_AUTO_LUNCH_DEFAULT = True
DEFAULT_SHEETS_WORKSHEET = "Worktime"
DEFAULT_AUTO_DEPARTURE_ENABLED = False
DEFAULT_AUTO_DEPARTURE_TIME = "15:00"
DEFAULT_AUTO_EXPORT_ENABLED = True
DEFAULT_AUTO_EXPORT_DELAY_HOURS = 3.0
DEFAULT_ARRIVAL_MARGIN_MINUTES = 0
DEFAULT_DEPARTURE_MARGIN_MINUTES = 0
MAX_MARGIN_MINUTES = 60

# Day types
DAY_TYPE_NORMAL = "normal"
DAY_TYPE_SICK = "sick"
DAY_TYPE_OFF = "off"
DAY_TYPE_FLEX = "flex"
DAY_TYPE_HOME = "home"  # Worked from home — counts like a normal day, no GPS

# Storage — keep original key and HA version so existing data is preserved.
# Internal schema migrations use "schema_version" inside the data dict.
STORAGE_KEY = f"{DOMAIN}.history"
STORAGE_VERSION = 1

# Notification action ids (kept in const for use in coordinator)
EVENT_NOTIFICATION_ACTION = "mobile_app_notification_action"
ACTION_LUNCH_YES = "WORKTIME_LUNCH_YES"
ACTION_LUNCH_NO = "WORKTIME_LUNCH_NO"
NOTIFICATION_TAG = "worktime_lunch_check"
ACTION_TIMEREPORT_YES = "WORKTIME_TIMEREPORT_YES"
ACTION_TIMEREPORT_NO = "WORKTIME_TIMEREPORT_NO"
NOTIFICATION_TAG_TIMEREPORT = "worktime_timereport"
ACTION_MORNING_ARRIVE = "WORKTIME_MORNING_ARRIVE"
ACTION_MORNING_HOME = "WORKTIME_MORNING_HOME"
ACTION_MORNING_SICK = "WORKTIME_MORNING_SICK"
NOTIFICATION_TAG_MORNING = "worktime_morning_reminder"
ACTION_DEPARTURE_NOW = "WORKTIME_DEPARTURE_NOW"
NOTIFICATION_TAG_DEPARTURE = "worktime_forgot_departure"

# New configuration keys (v2.9)
CONF_MORNING_REMINDER_ENABLED = "morning_reminder_enabled"
CONF_MORNING_REMINDER_TIME = "morning_reminder_time"
CONF_FORGOT_DEPARTURE_ENABLED = "forgot_departure_enabled"
CONF_FORGOT_DEPARTURE_OFFSET_MIN = "forgot_departure_offset_min"
CONF_ZONE_EXIT_GRACE_MIN = "zone_exit_grace_min"

DEFAULT_MORNING_REMINDER_ENABLED = False
DEFAULT_MORNING_REMINDER_TIME = "09:30"
DEFAULT_FORGOT_DEPARTURE_ENABLED = False
DEFAULT_FORGOT_DEPARTURE_OFFSET_MIN = 30
DEFAULT_ZONE_EXIT_GRACE_MIN = 5

# State / status values
STATUS_OFF_DUTY = "off_duty"
STATUS_AT_WORK = "at_work"
STATUS_DONE = "done"
STATUS_OVERTIME = "overtime"

LUNCH_UNKNOWN = "unknown"
LUNCH_YES = "yes"
LUNCH_NO = "no"

# Service names
SERVICE_SET_LUNCH = "set_lunch"
SERVICE_LOG_ARRIVAL = "log_arrival"
SERVICE_LOG_DEPARTURE = "log_departure"
SERVICE_RESET_TODAY = "reset_today"
SERVICE_EXPORT_TODAY = "export_today"
SERVICE_EXPORT_ALL = "export_all"
SERVICE_EDIT_DAY = "edit_day"
SERVICE_CLEAR_DAY = "clear_day"
