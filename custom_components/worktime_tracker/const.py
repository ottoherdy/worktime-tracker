"""Constants for the Worktime Tracker integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "worktime_tracker"

# Configuration keys
CONF_PERSON_ENTITY = "person_entity"
CONF_WORK_ZONE = "work_zone"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_LUNCH_TIME = "lunch_time"
CONF_WORKDAY_HOURS = "workday_hours"
CONF_LUNCH_DEDUCTION = "lunch_deduction"
CONF_WEEKLY_TARGET = "weekly_target"
CONF_SHEETS_ENTRY = "sheets_config_entry"
CONF_SHEETS_WORKSHEET = "sheets_worksheet"
CONF_AUTO_LUNCH_DEFAULT = "auto_lunch_default"
CONF_AUTO_DEPARTURE_ENABLED = "auto_departure_enabled"
CONF_AUTO_DEPARTURE_TIME = "auto_departure_time"
CONF_AUTO_EXPORT_ENABLED = "auto_export_enabled"
CONF_AUTO_EXPORT_DELAY_HOURS = "auto_export_delay_hours"

# Defaults
DEFAULT_LUNCH_TIME = "13:00"
DEFAULT_WORKDAY_HOURS = 8.5  # Includes lunch (so 8h net work)
DEFAULT_LUNCH_DEDUCTION = 0.5  # 30 minutes
DEFAULT_WEEKLY_TARGET = 40.0
DEFAULT_AUTO_LUNCH_DEFAULT = True
DEFAULT_SHEETS_WORKSHEET = "Worktime"
DEFAULT_AUTO_DEPARTURE_ENABLED = False
DEFAULT_AUTO_DEPARTURE_TIME = "15:00"
DEFAULT_AUTO_EXPORT_ENABLED = True
DEFAULT_AUTO_EXPORT_DELAY_HOURS = 3.0

# Day types
DAY_TYPE_NORMAL = "normal"
DAY_TYPE_SICK = "sick"

# Storage
STORAGE_KEY = f"{DOMAIN}.history"
STORAGE_VERSION = 1

# Events
EVENT_NOTIFICATION_ACTION = "mobile_app_notification_action"
EVENT_HISTORY_UPDATED = f"{DOMAIN}_history_updated"

# Notification action ids
ACTION_LUNCH_YES = "WORKTIME_LUNCH_YES"
ACTION_LUNCH_NO = "WORKTIME_LUNCH_NO"
NOTIFICATION_TAG = "worktime_lunch_check"
ACTION_TIMEREPORT_YES = "WORKTIME_TIMEREPORT_YES"
ACTION_TIMEREPORT_NO = "WORKTIME_TIMEREPORT_NO"
NOTIFICATION_TAG_TIMEREPORT = "worktime_timereport"

# State / status values
STATUS_OFF_DUTY = "off_duty"
STATUS_AT_WORK = "at_work"
STATUS_DONE = "done"
STATUS_OVERTIME = "overtime"

LUNCH_UNKNOWN = "unknown"
LUNCH_YES = "yes"
LUNCH_NO = "no"

# Polling / coordinator interval (used to refresh "time remaining" sensors)
UPDATE_INTERVAL = timedelta(seconds=30)

# Service names
SERVICE_SET_LUNCH = "set_lunch"
SERVICE_LOG_ARRIVAL = "log_arrival"
SERVICE_LOG_DEPARTURE = "log_departure"
SERVICE_RESET_TODAY = "reset_today"
SERVICE_EXPORT_HISTORY = "export_history"
SERVICE_EDIT_DAY = "edit_day"
SERVICE_LOG_SICK_DAY = "log_sick_day"
