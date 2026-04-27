# Worktime Tracker — Features & Requirements

## What it does

Automatically tracks work hours in Home Assistant based on zone presence (person entering/leaving the work zone). Stores history, calculates overtime, and exports to Google Sheets.

---

## Configuration (set up via UI)

| Setting | Description | Default |
|---|---|---|
| Person entity | `person.*` or `device_tracker.*` to track | — |
| Work zone | HA zone that counts as "at work" | — |
| Notify service | Mobile notification service (e.g. `mobile_app_iphone`) | — |
| Lunch time | When to send the lunch notification | 13:00 |
| Workday hours | Full workday length incl. lunch break | 8.5 h |
| Lunch deduction | Time deducted when lunch is taken | 0.5 h |
| Weekly target | Total hours target per week | 40 h |
| Google Sheets entry | Config entry ID for the native Sheets integration | — |
| Sheets worksheet | Name of the worksheet to write to | Worktime |
| Auto lunch default | Default lunch answer for the notification | Yes |

---

## Automatic tracking

- **Arrival** logged when person enters work zone
- **Departure** logged when person leaves work zone
- **Lunch notification** sent at the configured time asking "Did you have lunch today?" with Yes/No action buttons
- **Day rollover** at midnight: today's data is saved to history
- **Friday 16:00 notification** asking "Have you submitted your time report?" with Yes/Done and Not yet buttons — tapping Yes sends the day's row to Google Sheets

---

## Services

| Service | Description |
|---|---|
| `worktime_tracker.log_arrival` | Manually register arrival right now |
| `worktime_tracker.log_departure` | Manually register departure right now |
| `worktime_tracker.set_lunch` | Set lunch status (field: `had_lunch: true/false`) |
| `worktime_tracker.reset_today` | Clear today's data and start over |
| `worktime_tracker.export_history` | Send today's row to Google Sheets manually |
| `worktime_tracker.edit_day` | Edit arrival, departure or lunch for any date (fields: `date`, `arrival`, `departure`, `lunch`) |

---

## Sensors

### Today device

| Entity | Description |
|---|---|
| `sensor.worktime_tracker_arrival_time` | Arrival time (HH:MM or —) |
| `sensor.worktime_tracker_planned_end_time` | Calculated end time based on arrival + workday hours |
| `sensor.worktime_tracker_departure_time` | Departure time, or planned end if not yet departed |
| `sensor.worktime_tracker_hours_today` | Hours worked today (float) |
| `sensor.worktime_tracker_overtime_today` | Overtime today vs daily net target (float) |
| `sensor.worktime_tracker_time_remaining` | Minutes remaining; attributes include `human_readable` (e.g. "1h 23m") and `seconds_remaining` |
| `sensor.worktime_tracker_status` | Status enum: `off_duty` / `at_work` / `done` / `overtime` |
| `sensor.worktime_tracker_lunch_status` | Lunch enum: `yes` / `no` / `unknown` |
| `binary_sensor.worktime_tracker_at_work` | True when status is `at_work` or `overtime` |
| `binary_sensor.worktime_tracker_day_complete` | True when status is `done` |

### This Week device

| Entity | Description |
|---|---|
| `sensor.worktime_tracker_hours_week` | Total hours this week; attributes include `this_week`, `last_week` (Mon–Fri breakdown) and `recent_days` (last 5 days with hours) |
| `sensor.worktime_tracker_overtime_week` | Cumulative overtime this week vs days-worked × daily net target |
| `sensor.worktime_tracker_monday` … `_friday` | Per-day hours; attributes: `date`, `arrival`, `departure`, `lunch`, `human_readable` (e.g. "8h 45m") |

### Last Week device

| Entity | Description |
|---|---|
| `sensor.worktime_tracker_hours_last_week` | Total hours last week |
| `sensor.worktime_tracker_overtime_last_week` | Overtime last week |
| `sensor.worktime_tracker_last_monday` … `_last_friday` | Per-day hours last week; same attributes as this-week sensors |

### Edit Day device

| Entity | Description |
|---|---|
| `text.worktime_tracker_edit_date` | Date field for the edit form (YYYY-MM-DD), pre-filled with today |
| `text.worktime_tracker_edit_arrival` | Arrival field for the edit form (HH:MM) |
| `text.worktime_tracker_edit_departure` | Departure field for the edit form (HH:MM) |
| `select.worktime_tracker_edit_lunch` | Lunch field for the edit form (yes / no / unknown) |

---

## Google Sheets export

Columns written per row: `Date`, `Weekday`, `Arrival`, `Planned end`, `Departure`, `Lunch`, `Hours`, `Hours (rounded)` (rounded up to nearest quarter hour).

Export is **manual only** — triggered by `export_history` service or by answering Yes to the Friday time-report notification. It is not sent automatically on departure.

---

## Dashboard (dashboards/dashboard.yaml)

Built with `custom:bubble-card`. Sections:

1. **Work time** — arrival, departure, time remaining (shown as "1h 23m"), lunch status
2. **Quick actions** — log arrival/departure, set lunch yes/no, send to Sheets, reset today
3. **This week** — weekday sensors Mon–Fri with hours and times
4. **Chart** — ApexCharts bar chart: this week vs last week + 8h target line
5. **Edit day** — text/select helpers pre-filled via a script + Save button calling `edit_day`

### Edit day flow

1. Tap a weekday card → call script `worktime_pre_fill_edit_form` with the sensor entity — fills date/arrival/departure/lunch helpers automatically
2. Adjust any value by tapping the helper card (opens more-info)
3. Tap **Save changes** → calls `worktime_tracker.edit_day`

---

## Known requirements / open items

- Weekday cards should display hours as "8h 45m" (use `attribute: human_readable`)
- Edit day form should be pre-filled when tapping a day (requires HA script `worktime_pre_fill_edit_form`)
- Friday time-report notification only sends Sheets data if user confirms with Yes
- No automatic Sheets export on departure
