# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)

A complete **Home Assistant custom integration** for automatic work time tracking. Everything runs inside a single integration — no external automations or manual setup required. Fully configurable through the UI.

---

## How it works

The integration tracks a **person entity** (your phone / GPS). When you enter your configured work zone, arrival is logged. When you leave the zone after your configured auto-departure time (or press the button manually), departure is logged. Time counts continuously between arrival and departure regardless of brief zone exits (lunch runs, errands, etc.).

Each workday stores: arrival, departure, lunch status, hours worked, and overtime.

---

## Installation

### 1 — Install via HACS

1. Open **HACS** in Home Assistant
2. **Integrations** → three dots top right → **Custom repositories**
3. Add URL: `https://github.com/ottoherdy/worktime-tracker`, category: **Integration**
4. Search for **Worktime Tracker** → **Download**
5. Restart Home Assistant

### 2 — Configure

Go to **Settings → Devices & Services → + Add Integration → Worktime Tracker**

| Setting | Default | Description |
|---|---|---|
| Person entity | — | The `person.*` or `device_tracker.*` to track |
| Work zone | — | HA zone that counts as "at work" |
| Notify service | — | Mobile notification service (e.g. `mobile_app_your_phone`, without `notify.` prefix). Leave empty to disable lunch notifications |
| Lunch check time | `13:00` | When the lunch push notification is sent |
| Workday length | `8.5 h` | Full workday including lunch break |
| Lunch deduction | `0.5 h` | Deducted when lunch is answered "No" |
| Weekly target | `40 h` | Used for weekly overtime calculation |
| Assume lunch if no answer | On | At departure with no notification reply: assume lunch was taken |
| Auto departure | Off | Enable zone-exit based automatic departure |
| Auto departure time | `15:00` | Zone exits before this time are ignored (e.g. lunch runs). Zone exits at or after this time trigger automatic departure |
| Auto export to Sheets | On | Automatically send the day to Google Sheets after departure |
| Auto export delay | `3 h` | How long after departure to wait before sending |
| Google Sheets config entry | — | Config Entry ID of your Google Sheets integration |
| Sheets worksheet | `Worktime` | Name of the worksheet to write to |

All settings can be changed later under **Configure** on the integration card.

Two more values are editable directly on the device page as `number` entities (not in the config flow, because you may want to tweak them on the fly):

| Entity | Default | Description |
|---|---|---|
| `number.today_arrival_margin` | `0 min` | Minutes added to GPS-triggered arrival. `3` → 07:00 zone entry logged as 07:03. Manual button presses unaffected. |
| `number.today_departure_margin` | `0 min` | Minutes subtracted from GPS-triggered departure. `3` → 17:00 zone exit logged as 16:57. Manual button presses unaffected. |

### 3 — Add the dashboard

You have two options:

**Option A — Bundled custom card (simplest).** The integration ships its own Lovelace card and auto-loads it. Just add a manual card to any dashboard:

```yaml
type: custom:worktime-tracker-card
```

No HACS frontend dependencies. No resource registration. Hard-refresh the browser the first time after install if the card doesn't show up.

Inline edit: tap a row (or the ✏️ pencil) in any day table to open an edit modal pre-filled with that day's arrival, departure, lunch and type (normal / sick / off). Save calls `worktime_tracker.edit_day` — no script needed.

The card has a built-in **visual editor** — in dashboard edit mode, click the card → toggle sections with checkboxes, no YAML required. For YAML configuration, the keys are:

```yaml
type: custom:worktime-tracker-card
show_header: true            # title + status badge
show_times: true             # big arrival / planned end / hours row
show_progress: true          # progress bar
show_lunch_status: true      # lunch badge + remaining/overtime line
show_actions: true           # Log arrival / Log departure / Lunch ✓ / No lunch
show_auto_departure: true    # Auto-depart toggle + Reset
show_week: false             # compact one-line week summary
show_this_week: true         # this-week table (Mon–Fri) with totals/overtime
show_last_week: true         # last-week table with totals/overtime
show_recent: true            # rolling 7-day table
show_edit: true              # tap a row or pencil to edit
recent_days_limit: 7         # rows in the recent days table
```

Each week table footer shows total hours, overtime versus the daily target, and difference versus the weekly target (e.g. 40h).

#### Styling

Every visual property is exposed as a CSS variable — override in a theme or with `card-mod`:

```yaml
type: custom:worktime-tracker-card
card_mod:
  style: |
    :host {
      --wt-card-padding: 20px;
      --wt-radius: 18px;
      --wt-status-color: #6750a4;
      --wt-row-hover-bg: #6750a4;
      --wt-button-bg: #6750a4;
      --wt-divider-color: #ddd;
    }
```

Available variables: `--wt-card-padding`, `--wt-radius`, `--wt-status-color`, `--wt-row-hover-bg`, `--wt-row-hover-color`, `--wt-button-bg`, `--wt-button-color`, `--wt-table-header-color`, `--wt-divider-color`.

**Option B — Full dashboard YAML.** Open `dashboards/dashboard.yaml`, replace `person.your_person` with your own person entity, and paste the content into a new Lovelace view.

Required HACS frontend cards for option B:
- [Bubble Card](https://github.com/Clooos/Bubble-Card)
- [Flex Table Card](https://github.com/custom-cards/flex-table-card)

The full dashboard (option B) uses a script entity (`script.edit_worktime_day`) for the Edit day button. Create it once in HA:

1. Go to **Settings → Automations & Scenes → Scripts → Create Script → Edit in YAML**
2. Paste the contents of `dashboards/script_edit_worktime_day.yaml`
3. Save — HA will register it as `script.edit_worktime_day`

Alternatively, call the `worktime_tracker.edit_day` service directly from **Developer Tools → Actions** or any automation.

### 4 — Google Sheets (optional)

1. Install the official **Google Sheets** integration via **Settings → Devices & Services → + Add Integration**
2. Authenticate with your Google account
3. Copy the **Config Entry ID** from the integration (visible in the URL when you open it)
4. Paste it into the Worktime Tracker configuration

The integration appends one row per day with these columns:

| Column | Example | Notes |
|---|---|---|
| Date | `2026-04-28` | ISO format |
| Weekday | `Monday` | Full name |
| Type | `Normal` / `Sick` / `Off` | |
| Arrival | `08:12` | HH:MM |
| Planned end | `16:42` | HH:MM |
| Departure | `16:38` | HH:MM |
| Lunch | `yes` / `no` / `unknown` | |
| Hours | `8.43` | Exact float |
| Hours (rounded) | `8.50h` | Rounded up to nearest 15 min |
| Overtime | `0.43` | Hours vs daily target |
| Edited | `yes` / `no` | Marked when sent via edit_day |
| Punch-out missing | `yes` / `no` | `yes` when the 03:00 rollover finalized the day without a departure |

> **Note:** Format the `Hours` and `Overtime` columns in Google Sheets as **Number** (not Automatic) to avoid them being interpreted as dates.

---

## Features

### Automatic arrival & departure

- Arrival logged when you enter the work zone (first time per day)
- Time runs continuously — brief zone exits (lunch, errands) do not stop the clock
- Departure logged when you leave the zone **at or after** the configured auto-departure time (if the toggle is on), or manually via the dashboard button

### Lunch tracking

- A push notification is sent at the configured time asking "Did you have lunch today?"
- Answering **Yes** keeps the full workday length
- Answering **No** subtracts the lunch deduction from the total
- No answer → the "assume lunch" setting decides at departure

### Manual controls (dashboard buttons)

| Button | Action |
|---|---|
| Log arrival | Register arrival right now (ignores arrival margin) |
| Log departure | Register departure right now (ignores departure margin) |
| Lunch — Yes | Mark lunch as taken |
| Lunch — No | Mark lunch as not taken |
| Edit day | Change arrival, departure, lunch, or type (normal/sick/off) for any date |
| Send to Sheets | Manually send today's row |
| Reset today | Clear today's data and start over |
| Auto departure toggle | Enable/disable the auto-departure feature |

### Sick days

Use the **Edit day** button on the dashboard. Set **Type → Sick day** and optionally enter the number of hours (default: net workday hours, e.g. 8h).

- Counts toward hours and overtime just like a worked day
- Sent to Google Sheets with `Type: Sick`
- Supports partial days — specify hours or leave empty for the default

### Off days / vacation

Same flow as sick days, but pick **Type → Off**. Off days:

- Count `0` hours by default (override via the `hours` field if needed)
- Do **not** contribute to overtime
- Sent to Google Sheets with `Type: Off`

### Edit any day

Call `worktime_tracker.edit_day` (Developer Tools → Actions or automations). Lets you correct arrival, departure, lunch, or type for any historical date. Setting **Type: sick** or **Type: off** converts the day. The updated row is automatically sent to Google Sheets marked as `Edited: yes`.

### Arrival / departure margins

Two `number.*` entities (see Configure) let you trim a few minutes off each end of GPS-triggered events so the recorded workday matches when you actually start/stop working rather than when you cross the geofence. Manual button presses log the exact time and ignore the margins.

### Auto export to Sheets

After departure is logged, a timer starts (configurable, default 3 hours). When the timer fires, the day is automatically sent to Google Sheets. This gives you time to correct anything before the row is written.

You can also send manually at any time using the **Send to Sheets** button.

### Day rollover

At 03:00 each night the integration resets for the new day. If no departure was registered (e.g. GPS didn't trigger), the day is finalized with `Punch-out missing: yes` — you can correct it later with **Edit day**.

### Friday time-report reminder

Every Friday at 16:00 the integration sends a notification asking "Have you submitted your time report?" via the configured notify service. Answering **Yes, done** triggers a manual Google Sheets export of today's row. Disable by leaving the notify service blank.

---

## Entities

### Sensors

| Entity | State | Key attributes |
|---|---|---|
| `sensor.today_hours_today` | Hours worked today (float) | `arrival`, `departure`, `planned_end`, `lunch`, `human_readable`, `overtime`, `time_remaining`, `status`, `recent_days` (last 60 days) |
| `sensor.today_status` | `off_duty` / `at_work` / `overtime` / `done` | — |
| `sensor.this_week_hours_this_week` | Total hours this ISO week | `hours`, `overtime`, `weekly_target`, `days` (Mon–Fri breakdown) |
| `sensor.last_week_hours_last_week` | Total hours last ISO week | `hours`, `overtime`, `days` |
| `sensor.this_month_hours_this_month` | Total hours this calendar month | `hours`, `human_readable`, `overtime`, `month` |
| `sensor.last_month_hours_last_month` | Total hours last calendar month | `hours`, `human_readable`, `overtime`, `month` |

Each entry in the `days` attribute list contains: `date`, `weekday`, `arrival`, `departure`, `lunch`, `hours`, `human_readable`.

### Binary sensors

| Entity | On when |
|---|---|
| `binary_sensor.today_at_work` | Status is `at_work` or `overtime` |
| `binary_sensor.today_day_complete` | Status is `done` |

### Switch

| Entity | Description |
|---|---|
| `switch.today_auto_departure` | Toggle auto-departure on/off from the dashboard |

### Number

| Entity | Range | Description |
|---|---|---|
| `number.today_arrival_margin` | 0–60 min | Minutes added to GPS-triggered arrival (e.g. `3` → arrival logged 3 min later than zone entry). `0` disables. Manual button presses are unaffected. |
| `number.today_departure_margin` | 0–60 min | Minutes subtracted from GPS-triggered departure (e.g. `3` → departure logged 3 min earlier than zone exit). `0` disables. Manual button presses are unaffected. |

---

## Services

| Service | Fields | Description |
|---|---|---|
| `worktime_tracker.log_arrival` | — | Register arrival right now (manual — ignores arrival margin) |
| `worktime_tracker.log_departure` | — | Register departure right now (manual — ignores departure margin) |
| `worktime_tracker.set_lunch` | `had_lunch: true/false` | Set lunch status |
| `worktime_tracker.reset_today` | — | Clear today's data |
| `worktime_tracker.export_today` | — | Send today's row to Google Sheets now |
| `worktime_tracker.edit_day` | `date`, `type` (`normal` / `sick` / `off`), `arrival`, `departure`, `lunch`, `hours` — all optional | Edit any day. `type: sick` logs a sick day (default = net workday hours); `type: off` logs vacation (default 0h). Sends updated row to Sheets marked as edited. |

---

## Status values

| Status | Meaning |
|---|---|
| `off_duty` | No arrival registered today |
| `at_work` | Arrived, planned end not yet passed |
| `overtime` | Still at work past the planned end time |
| `done` | Departure has been registered |

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| Arrival not logged automatically | Check that the person entity state matches the zone name (case-insensitive). Enable debug logging for `custom_components.worktime_tracker` to see state change events. |
| Lunch notification not arriving | Verify `notify_service` is set without the `notify.` prefix |
| Rows not appearing in Sheets | Check that the Google Sheets integration is installed and the Config Entry ID is correct |
| Hours column shows as a date in Sheets | Format the column as **Number** in Google Sheets |
| Planned end time wrong after editing arrival | Reload the integration after editing |

---

## Repository structure

```
worktime-tracker/
├── custom_components/worktime_tracker/   ← integration (HACS installs this)
├── dashboards/dashboard.yaml             ← example Lovelace view
├── hacs.json                             ← HACS metadata
└── .github/workflows/validate.yml        ← hassfest + HACS validation
```

---

## License

MIT — see [LICENSE](LICENSE).
