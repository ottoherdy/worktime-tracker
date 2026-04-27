# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)

A complete **Home Assistant custom integration** for automatic work time tracking. Everything runs inside a single integration — no automations, no manual setup. Fully configurable through the UI.

## Features

- **Automatic time tracking** via a zone — arrival and departure logged automatically
- **Lunch notification** with Yes/No buttons — your answer adjusts the planned end time
- **Daily log to Google Sheets** with weekday, times, hours, and quarter-rounded hours
- **Dashboard** with weekly overview, bar chart (this week vs last week), and the 5 most recent days
- **Scriptable widget** for iOS showing time remaining or overtime as a progress circle

## Repository structure

```
worktime-tracker/
├── custom_components/worktime_tracker/   ← the integration (HACS installs this)
├── dashboards/dashboard.yaml             ← Lovelace view
├── scriptable/worktime_widget.js         ← iOS widget
├── hacs.json                             ← HACS metadata
└── .github/workflows/validate.yml        ← hassfest + HACS validation
```

## Installation

### Step 1 — Install via HACS

1. Open HACS in Home Assistant
2. **Integrations** → three dots top right → **Custom repositories**
3. Add URL: `https://github.com/ottoherdy/worktime-tracker`, category: **Integration**
4. Search for **Worktime Tracker** → **Download**
5. Restart Home Assistant

### Step 2 — Configure

`Settings → Devices & Services → + Add Integration → "Worktime Tracker"`

| Field | Example | Description |
|---|---|---|
| Person or device tracker | `person.your_name` | The person being tracked |
| Work zone | `zone.work` | Being inside this zone counts as "at work" |
| Notify service | `mobile_app_your_phone` | Without the `notify.` prefix. Leave empty for no lunch notification |
| Lunch check time | `13:00` | When the lunch push notification is sent |
| Workday length | `8.5` | Including lunch (8h net work + 0.5h lunch) |
| Lunch break | `0.5` | Deducted when answering "No" to the lunch prompt |
| Weekly target | `40` | Used for overtime calculation |
| Assume lunch if no answer | On | At departure with no answer: count lunch as taken |

All settings can be changed later via **Configure** on the integration.

### Step 3 — Add the dashboard

Open `dashboards/dashboard.yaml` and paste it into a new or existing Lovelace dashboard.

Requires two HACS frontend cards:
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)

### Step 4 — Google Sheets (optional)

Requires the official [Google Sheets integration](https://www.home-assistant.io/integrations/google_sheets/) to be installed in Home Assistant.

1. Install **Google Sheets** via `Settings → Devices & Services → + Add Integration`
2. Authenticate with your Google account
3. Go to **Configure** on the Worktime Tracker integration
4. Enter the **Config Entry ID** for the Google Sheets integration and a **worksheet name**

Each day a row is automatically appended with the following columns:

| Column | Example |
|---|---|
| Date | 2026-04-28 |
| Weekday | Monday |
| Arrival | 08:12 |
| Planned end | 16:42 |
| Departure | 16:38 |
| Lunch | yes |
| Hours | 8.43 |
| Hours (rounded) | 8.5 |

### Step 5 — Scriptable iOS widget (optional)

1. Install [Scriptable](https://apps.apple.com/app/scriptable/id1405459188)
2. Create a new script and paste in `scriptable/worktime_widget.js`
3. Set `HA_URL` and `HA_TOKEN` (create a Long-Lived Token: HA profile → Security)
4. Add a Scriptable widget to your home screen, **Medium** size

## Entities

| Entity | Description |
|---|---|
| `sensor.worktime_tracker_arrival_time` | Arrival (timestamp) |
| `sensor.worktime_tracker_planned_end_time` | Planned end time |
| `sensor.worktime_tracker_departure_time` | Departure time |
| `sensor.worktime_tracker_hours_today` | Hours worked today |
| `sensor.worktime_tracker_hours_week` | Weekly total + attributes `this_week`, `last_week`, `recent_days` |
| `sensor.worktime_tracker_overtime_week` | Overtime against the weekly target |
| `sensor.worktime_tracker_time_remaining` | Minutes remaining (+ `human_readable` attribute) |
| `sensor.worktime_tracker_status` | `off_duty` / `at_work` / `done` / `overtime` |
| `sensor.worktime_tracker_lunch_status` | `yes` / `no` / `unknown` |
| `binary_sensor.worktime_tracker_at_work` | Currently at work |
| `binary_sensor.worktime_tracker_day_complete` | Day finished |

## Services

| Service | Data | Description |
|---|---|---|
| `worktime_tracker.set_lunch` | `had_lunch: true/false` | Set lunch status |
| `worktime_tracker.log_arrival` | – | Manually register arrival |
| `worktime_tracker.log_departure` | – | Manually register departure |
| `worktime_tracker.reset_today` | – | Clear today's data |
| `worktime_tracker.export_history` | – | Re-send today's row to Sheets |

## How it works

```
Person enters the work zone
        ↓
arrival = now,  planned_end = arrival + workday length

At 13:00 if still at work → push: [Yes, had lunch] [No]
   "No" → planned_end -= lunch break
   No answer → "assume lunch" flag decides at departure

Person leaves the zone
        ↓
1) Calculate hours worked (minus lunch if "Yes")
2) Save to local HA storage
3) Append row to Google Sheets (if configured)
4) Update all sensors
```

### Status values

| Status | When |
|---|---|
| `off_duty` | No arrival registered today |
| `at_work` | Arrived, planned end not passed, no departure |
| `overtime` | Still at work past planned end time |
| `done` | Departure registered |

## Troubleshooting

| Symptom | Solution |
|---|---|
| Lunch notification not arriving | Check that `notify_service` is set without the `notify.` prefix |
| Rows not appearing in Sheets | Verify the Google Sheets integration is installed and the Config Entry ID is correct |
| ApexCharts chart is empty | The sensor needs at least one completed day in its history |
| Scriptable widget shows error | Check that `HA_URL` and `HA_TOKEN` are correctly filled in |

## Contributing

PRs welcome. CI runs `hassfest`, HACS validation, and a Python compile check on every push.

## License

MIT — see [LICENSE](LICENSE).
