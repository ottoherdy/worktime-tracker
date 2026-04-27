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
| `worktime_tracker.edit_day` | Edit arrival, departure or lunch for any date (fields: `date`, `arrival` HH:MM, `departure` HH:MM, `lunch`). Automatically pushes the updated row to Sheets marked as "Edited: yes". |

---

## Sensors (4 total)

### Today device

| Entity | State | Key attributes |
|---|---|---|
| `sensor.worktime_tracker_today` | Hours today (float) | `arrival`, `departure`, `planned_end`, `lunch`, `human_readable` ("8h 45m"), `overtime`, `time_remaining`, `status` |
| `sensor.worktime_tracker_status` | `off_duty` / `at_work` / `done` / `overtime` | — |
| `binary_sensor.worktime_tracker_at_work` | True when at_work or overtime | — |
| `binary_sensor.worktime_tracker_day_complete` | True when done | — |

### This Week device

| Entity | State | Key attributes |
|---|---|---|
| `sensor.worktime_tracker_this_week` | Total hours this week (float) | `overtime`, `weekly_target`, `days` (Mon–Fri list) |

Each item in `days`: `date`, `weekday` (Mon/Tue/…), `arrival`, `departure`, `lunch`, `hours`, `human_readable`

### Last Week device

| Entity | State | Key attributes |
|---|---|---|
| `sensor.worktime_tracker_last_week` | Total hours last week (float) | `overtime`, `days` (Mon–Fri list, same structure) |

---

## Google Sheets export

Columns: `Date`, `Weekday`, `Arrival`, `Planned end`, `Departure`, `Lunch`, `Hours`, `Hours (rounded)`, `Edited`

- `Edited: no` for normal exports (manual or Friday notification)
- `Edited: yes` when row was sent via `edit_day` service

Export is **not** automatic on departure — triggered manually via `export_history` service or Friday notification.

---

## Dashboard (dashboards/dashboard.yaml)

Built with `custom:bubble-card`. Sections:

1. **Work time** — arrival, departure, time remaining, lunch (all from `sensor.worktime_tracker_today` attributes)
2. **Quick actions** — log arrival/departure, set lunch yes/no, send to Sheets, reset today
3. **This week** — markdown card looping `sensor.worktime_tracker_this_week.attributes.days`
4. **Last week** — same for last week
5. **Chart** — ApexCharts bar chart: this week vs last week + 8h target line

---

## Edit day flow

1. Call `worktime_tracker.edit_day` with `date`, `arrival`, `departure`, `lunch`
   - Via Developer Tools > Services, or
   - Via an HA script with fields (create in Settings → Scripts):
     ```yaml
     alias: Edit worktime day
     fields:
       date:
         description: Date to edit (YYYY-MM-DD, leave empty for today)
         example: "2026-04-25"
       arrival:
         description: Arrival time (HH:MM)
         example: "08:15"
       departure:
         description: Departure time (HH:MM)
         example: "16:30"
       lunch:
         description: Lunch status (yes/no/unknown)
         selector:
           select:
             options: [yes, no, unknown]
     sequence:
       - action: worktime_tracker.edit_day
         data:
           date: "{{ date }}"
           arrival: "{{ arrival }}"
           departure: "{{ departure }}"
           lunch: "{{ lunch }}"
     ```
2. History is updated locally and the updated row is automatically pushed to Sheets (marked Edited: yes)
