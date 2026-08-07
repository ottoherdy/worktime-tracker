# Google Sheets

Exporting is optional — the integration keeps its own history either way. Use it
if you want the data somewhere you can pivot, chart, or hand to a payroll system.

There are two separate paths, and you only need one.

[← Back to README](../README.md)

---

## Which one do I want?

| | Official integration | Apps Script webhook |
|---|---|---|
| Setup | Add an integration, paste an ID | Paste a script, deploy a web app |
| Columns | 15, including revisions and audit fields | 6, just the essentials |
| Google account | OAuth through Home Assistant | The script runs as you |
| Best for | Most people | When you cannot or would rather not connect an account to HA |

**Start with the official integration.** The Apps Script exists for setups where
the Google Sheets integration is not an option, and it writes a simpler sheet.

---

## Option 1 — the official integration

1. **Settings → Devices & Services → + Add Integration → Google Sheets**
2. Authenticate with your Google account
3. Open the integration and copy the **Config Entry ID** from the browser URL
4. Paste it into Worktime Tracker's configuration, along with the worksheet name

That is it. After departure, the day is sent automatically once the auto-export
delay has passed (3 hours by default, so there is time to correct mistakes).

### Columns

| Column | Example | Notes |
|---|---|---|
| Date | `2026-04-28` | ISO |
| Weekday | `Monday` | Full name |
| Type | `Normal` | Or `Sick`, `Off`, `Flex`, … |
| Arrival | `08:12` | HH:MM |
| Planned end | `16:42` | HH:MM |
| Departure | `16:38` | HH:MM |
| Lunch | `yes` | Or `no`, `unknown` |
| Hours | `8.43` | Exact float |
| Hours (rounded) | `8.50h` | Rounded up to the nearest 15 min |
| Overtime | `0.43` | Against the daily target |
| Edited | `yes` | Set when the row came from `edit_day` |
| Punch-out missing | `no` | `yes` when the 03:00 rollover closed the day with no departure |
| Rev | `1` | Bumped each time the day changes |
| Source | `auto` | Or `manual`, `edit`, `bulk` |
| Updated at | `2026-04-28T16:41:09+02:00` | When the row was written |

### It appends, it does not overwrite

Editing a day that was already exported appends a **new row** with `Rev`
incremented and `Edited: yes`. The original stays put. The sheet is an
append-only log, so sort or filter on `Date` + `Rev` to see the current state of
each day.

That is deliberate — you keep the audit trail of what was reported and when.

> **Format the `Hours` and `Overtime` columns as Number**, not Automatic.
> Left on Automatic, Google Sheets reads values like `8.43` as dates.

---

## Option 2 — the Apps Script webhook

`apps_script/google_apps_script.gs` receives a POST and writes six columns:
date, arrival, planned end, departure, lunch, hours. One row per day, updated in
place when the same date is posted again.

1. Open the target sheet → **Extensions → Apps Script**
2. Paste in the contents of `apps_script/google_apps_script.gs`
3. **Deploy → New deployment → Web app**, with *Execute as* **Me** and *Who has
   access* **Anyone**
4. Copy the deployment URL into Worktime Tracker's Sheets webhook URL setting

Two constants at the top of the script are worth a look:

```javascript
const SHEET_NAME = "Worktime";
const HEADERS = ["Date", "Arrival", "Planned end", "Departure", "Lunch", "Hours"];
```

`SHEET_NAME` must match the worksheet name in the integration's configuration.
`HEADERS` is only used to seed an empty sheet — translate it freely. A sheet that
already has content keeps its own header row untouched, whatever language it is
in, so pointing the script at an existing sheet will not shift your data.

---

## Catching up an existing history

Set Sheets up after months of tracking? Push everything at once:

```yaml
action: worktime_tracker.export_all
```

It skips days that are already there and unchanged, so it is safe to re-run. See
[`export_all`](services.md#export_all) for narrowing by date or forcing a resend.

---

## When rows do not appear

Check **Settings → System → Logs** for:

```
Worktime: google_sheets not installed — skipping export
```

That means the Google Sheets integration is missing or the Config Entry ID is
wrong. More symptoms in [Troubleshooting](troubleshooting.md).
