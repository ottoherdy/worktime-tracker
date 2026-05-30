# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)

A complete **Home Assistant custom integration** for automatic work time tracking. Everything runs inside a single integration — no external automations or manual setup required. Fully configurable through the UI, and ships with its own phone-first Lovelace card.

---

## How it works

The integration tracks a **person entity** (your phone / GPS). When you enter your configured work zone, arrival is logged. When you leave the zone after your configured auto-departure time — or when you press the button manually — departure is logged. Time counts continuously between arrival and departure, regardless of brief zone exits (lunch runs, errands, etc.).

Each workday stores arrival, departure, lunch status, hours worked, and overtime. Days are kept locally and can optionally be mirrored to a Google Sheet, with re-export of edited days handled automatically.

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
| Instance name | `Worktime Tracker` | Used as the slug for entities and routing — set a distinct value (e.g. `Otto`, `Ellen`) when adding more than one instance |
| Person entity | — | The `person.*` or `device_tracker.*` to track |
| Work zone | — | HA zone that counts as "at work" |
| Notify service | — | Mobile notification service (e.g. `mobile_app_your_phone`, without `notify.` prefix). Leave empty to disable lunch and Friday notifications |
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

The integration ships a phone-first Lovelace card and auto-loads it. Just add a manual card to any dashboard:

```yaml
type: custom:worktime-tracker-card
```

The card is capped at 420 px wide by default — designed for a phone screen first, renders cleanly on desktop too. No HACS frontend dependencies, no resource registration. Hard-refresh the browser the first time after install if the card doesn't show up.

The card sections (top to bottom):

1. **Topbar** — today's date, centered (off by default)
2. **Today** — big elapsed time (`9h 34m`), target sub-line, progress bar, In / Out / Lunch strip, action buttons (Log arrival / Reset / Log departure) plus Lunch + Auto-out toggles, "On the clock" pulse pill in the header
3. **This week** — Mon–Fri list with weekday + date + arrival → departure + hours, "today" row highlighted, totals footer (`3 days · 28h 03m`)
4. **Last week** — same layout
5. **This month** / **Last month** (default off) — compact summary cards with total hours + overtime
6. **History** — compact list with a mini-bar per day; bar fills warn-orange when over the daily target
7. **Look up day** — date picker that finds any day across history; **Edit** opens the modal pre-filled, **Add** opens a blank modal for the picked date so you can seed days that have no data yet
8. **Footer** — `Saved locally` left, `Export` / `Sheets` right (both call `worktime_tracker.export_today`). Optional **Export all** link (off by default) triggers `worktime_tracker.export_all` with a confirm dialog

Inline edit: tap any row (or the ✏️ pencil) in a day table to open the edit modal pre-filled with that day's arrival, departure, lunch and type (normal / sick / off / flex). Save calls `worktime_tracker.edit_day`. Reset today shows a confirm dialog before clearing.

#### Visual editor

Click the card in dashboard edit mode for a full visual editor — section toggles, button toggles, label rewrites, color preset / custom colors, theme (auto / light / dark), font scale, padding, corner radius, max width, time format. Text inputs (entity prefix, labels) keep focus while you type.

YAML keys (all optional):

```yaml
type: custom:worktime-tracker-card

# Sections
show_topbar: false           # centered date
show_today: true             # Today card with elapsed time and actions
show_this_week: true         # This week list with totals
show_last_week: true         # Last week list
show_this_month: false       # This month hours + overtime summary
show_last_month: false       # Last month summary
show_history: true           # History compact list
show_lookup: true            # Look up / add day picker
show_footer: true            # "Saved locally" + Export/Sheets links
show_edit: true              # edit pencil + row-tap → modal

# Buttons (inside the Today card)
show_btn_arrival: true
show_btn_reset: true
show_btn_departure: true
show_btn_lunch: true
show_btn_auto: true
show_btn_export_all: false   # extra "Export all" link in the footer

# Size & layout
padding: 14                  # outer padding in pixels
corner_radius: 16
max_width: 420               # card width cap; set 0 for fluid
font_scale: "M"              # S / M / L
compact: false

# Theme & colour
theme: "auto"                # auto / light / dark
color_preset: "orange"       # orange / blue / green / purple / slate
color_bg: ""                 # custom hex; overrides preset
color_card: ""
color_ink: ""
color_accent: ""
color_warn: ""

# Labels (rewrite section titles)
title_today: "Today"
title_this_week: "This week"
title_last_week: "Last week"
title_this_month: "This month"
title_last_month: "Last month"
title_history: "History"
title_lookup: "Look up day"

# Formats
date_format: "iso"           # iso / locale
time_format: "hm"            # hm (9h 30m) / decimal / colon (9:30)

# History
history_limit: 10            # rows in the history list

# Multi-instance
entity_prefix: ""            # slug of the instance to bind to — see below
```

#### Multiple instances

The integration accepts more than one config entry. Each one gets its own
**instance name** (default `Worktime Tracker`) — set a distinct value like
`Otto` or `Ellen` on the second instance to avoid entity-ID collisions, and
each instance gets its own isolated storage file so history can't bleed
across people.

The card defaults to reading `sensor.today_hours_today` etc. (the original
instance). To bind a card to another instance, set `entity_prefix` to its
slug — e.g. instance name `Ellen` → `entity_prefix: ellen`, instance name
`Worktime Tracker Otto` → `entity_prefix: worktime_tracker_otto`. The card
then reads `sensor.<prefix>_today_hours_today` and stamps service calls with
that prefix so only the matching coordinator responds.

If `edit_day` (or any action) does nothing for an instance, check
**Settings → System → Logs** for a `Worktime: edit_day for … matched no
instance` warning — it lists the active slugs so you can fix the
`entity_prefix` value on the card.

#### Theming

Every visual token is a CSS variable on `:host` — override in a theme, with
`card_mod`, or via the visual editor's colour fields:

```yaml
type: custom:worktime-tracker-card
card_mod:
  style: |
    :host {
      --wt-bg:     #1c1c1f;
      --wt-card:   #25252a;
      --wt-paper:  #2d2d33;
      --wt-ink:    #f4f3ee;
      --wt-ink-2:  #b6b6be;
      --wt-muted:  #8a8a94;
      --wt-line:   #3a3a44;
      --wt-line-2: #2f2f36;
      --wt-accent: #8a82e8;
    }
```

Available variables: `--wt-bg`, `--wt-paper`, `--wt-card`, `--wt-ink`, `--wt-ink-2`, `--wt-muted`, `--wt-muted-2`, `--wt-line`, `--wt-line-2`, `--wt-accent`, `--wt-accent-soft`, `--wt-good`, `--wt-warn`, `--wt-danger`.

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
| Type | `Normal` / `Sick` / `Off` / `Flex` | |
| Arrival | `08:12` | HH:MM |
| Planned end | `16:42` | HH:MM |
| Departure | `16:38` | HH:MM |
| Lunch | `yes` / `no` / `unknown` | |
| Hours | `8.43` | Exact float |
| Hours (rounded) | `8.50h` | Rounded up to nearest 15 min |
| Overtime | `0.43` | Hours vs daily target |
| Edited | `yes` / `no` | Marked when sent via `edit_day` |
| Punch-out missing | `yes` / `no` | `yes` when the 03:00 rollover finalized the day without a departure |
| Rev | `1`, `2`, … | Bumped each time the day's content changes |
| Source | `auto` / `manual` / `edit` / `bulk` | Which code path produced the row |
| Updated at | `2026-04-28T16:41:09+02:00` | When this row was appended |

When you edit a previously exported day, a new row is appended with
`Rev` incremented and `Edited: yes`. The original row is left intact, so
the sheet acts as an append-only log — sort or filter on `Date` + `Rev`
for the latest state.

> **Note:** Format the `Hours` and `Overtime` columns in Google Sheets as **Number** (not Automatic) to avoid them being interpreted as dates.

---

## Features

### Automatic arrival & departure

- Arrival logged when you enter the work zone (first time per day)
- Time runs continuously — brief zone exits (lunch, errands) do not stop the clock
- Departure logged when you leave the zone **at or after** the configured auto-departure time (if the toggle is on), or manually via the dashboard button
- Zone matching uses the zone's **friendly name** (what HA actually stores in `person.*` state), so multi-word zones like `Ellen's Office` work the same as single-word slugs

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
| Lunch — Yes / No | Set lunch status |
| Auto-out toggle | Enable / disable zone-exit based automatic departure |
| Reset today | Clear today's data and start over (confirm prompt) |
| Edit / Add day | Open the modal for any date — change arrival, departure, lunch, type, or hours, or add a blank day from the date picker |
| Export | Send today's row to Sheets |
| Export all | Send every locally-known day that's missing or changed in Sheets (confirm prompt; optional footer link) |

### Sick days

Open the edit modal (row tap, pencil, or the Look-up box's Add/Edit
button). Set **Type → Sick** and optionally enter the number of hours
(default: net workday hours, e.g. 8h).

- Counts toward hours and overtime just like a worked day
- Sent to Google Sheets with `Type: Sick`
- Supports partial days — specify hours or leave empty for the default

### Off days / vacation

Same flow, but pick **Type → Off**. Off days:

- Count `0` hours by default (override via the `hours` field if needed)
- Do **not** contribute to overtime
- Sent to Google Sheets with `Type: Off`

### Flex days

Pick **Type → Flex** to log a flex-leave day. Defaults to 0 hours; set
`hours` to count it against banked overtime. Sent to Sheets with
`Type: Flex`.

### Edit any day

Call `worktime_tracker.edit_day` directly (Developer Tools → Actions,
automations) or from the modal in the card. Lets you correct arrival,
departure, lunch, type, or hours for any historical date. Setting
**Type: sick / off / flex** converts the day. The updated row is sent
to Sheets marked `Edited: yes` and with `Rev` incremented.

### Arrival / departure margins

Two `number.*` entities (see Configure) let you trim a few minutes off
each end of GPS-triggered events so the recorded workday matches when
you actually start / stop working rather than when you cross the
geofence. Manual button presses log the exact time and ignore the
margins.

### Auto export to Sheets

After departure is logged, a timer starts (configurable, default 3 h).
When the timer fires the day is automatically sent to Google Sheets.
This gives you time to correct anything before the row is written.

You can also push manually any time using the **Export** button, or
`worktime_tracker.export_today`.

### Bulk export — `export_all`

`worktime_tracker.export_all` walks the full local history (and leave
records) and re-emits each day to Sheets that is either missing there or
whose content has changed since the last push (compared via SHA-256
fingerprint, so unchanged days are skipped). Useful after:

- Setting up Sheets for the first time on an instance that already has history
- Bulk-editing days locally and wanting the sheet caught up
- Migrating data between sheets

Optional parameters:

- `since: "2026-01-01"` — only consider dates on or after this ISO date
- `force: true` — re-send even days whose fingerprint hasn't changed

The footer's **Export all** link (gated on `show_btn_export_all`) calls
this with a confirm dialog.

### Day rollover

At 03:00 each night the integration resets for the new day. If no
departure was registered (e.g. GPS didn't trigger), the day is finalized
with `Punch-out missing: yes` — you can correct it later from the edit
modal.

### Friday time-report reminder

Every Friday at 16:00 the integration sends a notification asking
"Have you submitted your time report?" via the configured notify service.
Answering **Yes, done** triggers a manual Google Sheets export of today's
row. Disable by leaving the notify service blank.

---

## Entities

All entities are prefixed with the instance's slug — `today_*` /
`this_week_*` / etc. on the default instance, `<prefix>_today_*` etc.
on additional instances.

### Sensors

| Entity | State | Key attributes |
|---|---|---|
| `sensor.today_hours_today` | Hours worked today (float) | `arrival`, `departure`, `planned_end`, `lunch`, `human_readable`, `overtime`, `time_remaining`, `status`, `recent_days` (last 60 days) |
| `sensor.today_status` | `off_duty` / `at_work` / `overtime` / `done` | — |
| `sensor.this_week_hours_this_week` | Total hours this ISO week | `hours`, `overtime`, `weekly_target`, `days` (Mon–Fri breakdown) |
| `sensor.last_week_hours_last_week` | Total hours last ISO week | `hours`, `overtime`, `days` |
| `sensor.this_month_hours_this_month` | Total hours this calendar month | `hours`, `human_readable`, `overtime`, `month` |
| `sensor.last_month_hours_last_month` | Total hours last calendar month | `hours`, `human_readable`, `overtime`, `month` |

Each entry in the `days` / `recent_days` lists contains: `date`, `weekday`, `arrival`, `departure`, `lunch`, `hours`, `human_readable`, `type`.

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
| `number.today_arrival_margin` | 0–60 min | Minutes added to GPS-triggered arrival. `0` disables. Manual button presses unaffected. |
| `number.today_departure_margin` | 0–60 min | Minutes subtracted from GPS-triggered departure. `0` disables. Manual button presses unaffected. |

---

## Services

All services accept an optional `entry_prefix` field to target a single
instance. Omit it on single-instance setups; on multi-instance setups
the card fills it in automatically based on the card's `entity_prefix`.

| Service | Fields | Description |
|---|---|---|
| `worktime_tracker.log_arrival` | — | Register arrival right now (manual — ignores arrival margin) |
| `worktime_tracker.log_departure` | — | Register departure right now (manual — ignores departure margin) |
| `worktime_tracker.set_lunch` | `had_lunch: true/false` | Set lunch status |
| `worktime_tracker.reset_today` | — | Clear today's data |
| `worktime_tracker.export_today` | — | Send today's row to Google Sheets now |
| `worktime_tracker.export_all` | `since` (ISO date, optional), `force` (bool, default `false`) | Re-emit every locally-known day to Sheets that is missing or changed |
| `worktime_tracker.edit_day` | `date`, `type` (`normal` / `sick` / `off` / `flex`), `arrival`, `departure`, `lunch`, `hours` — all optional | Edit (or create) any day. `type: sick` defaults to net workday hours; `type: off` / `flex` default to 0 h. Sends updated row to Sheets marked as edited with bumped `Rev`. |

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
| Arrival not logged automatically | Check the zone — `person.*` state stores the zone's **friendly name**, not its entity_id slug. Multi-word friendly names work as of v2.8.3. Enable debug logging for `custom_components.worktime_tracker` to see state-change events. |
| Lunch notification not arriving | Verify the notify service is set without the `notify.` prefix |
| Rows not appearing in Sheets | Check that the Google Sheets integration is installed and the Config Entry ID is correct. Look for a `Worktime: google_sheets not installed — skipping export` warning in the log. |
| `Hours` column shows as a date in Sheets | Format the column as **Number** in Google Sheets |
| Card actions do nothing on a multi-instance setup | Check the log for `Worktime: … matched no instance — Active slugs: [...]` and set the card's `entity_prefix` to one of the listed slugs |
| Planned end time wrong after editing arrival | Reload the integration after editing |
| Editor text inputs lose focus on every keystroke | Fixed in v2.8.2 — update the integration |

---

## Repository structure

```
worktime-tracker/
├── custom_components/worktime_tracker/   ← integration + bundled card (HACS installs this)
├── dashboards/dashboard.yaml             ← example Lovelace view (legacy, prefer the bundled card)
├── apps_script/                          ← optional Google Apps Script helpers
├── scriptable/                           ← optional iOS widget script
├── hacs.json                             ← HACS metadata
└── .github/workflows/validate.yml        ← hassfest + HACS validation
```

---

## License

MIT — see [LICENSE](LICENSE).
