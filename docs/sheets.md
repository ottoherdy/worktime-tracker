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

Written in this order:

| Column | Example | Notes |
|---|---|---|
| Date | `2026-04-28` | ISO |
| Week | `2026-W18` | ISO year and week |
| Month | `2026-04` | |
| Weekday | `Monday` | Full name |
| Type | `Normal` | Or `Sick`, `Off`, `Flex`, … |
| Arrival | `08:12` | HH:MM |
| Planned end | `16:42` | HH:MM |
| Departure | `16:38` | HH:MM |
| Lunch | `yes` | Or `no`, `unknown` |
| Hours | `8.43` | Exact float |
| Hours (rounded) | `8.50h` | Rounded up to the nearest 15 min |
| Overtime | `0.43` | Against the daily target |
| Top-up type | `flex` | Empty unless part of the day was split off |
| Top-up hours | `4` | |
| Edited | `yes` | Set when the row came from `edit_day` |
| Punch-out missing | `no` | `yes` when the 03:00 rollover closed the day with no departure |
| Rev | `1` | Bumped each time the day changes |
| Source | `auto` | Or `manual`, `edit`, `bulk` |
| Updated at | `2026-04-28T16:41:09+02:00` | When the row was written |

> **Give the sheet at least 20 columns.** That is 19 above plus one more:
> Home Assistant's `google_sheets` integration stamps a `created` column onto
> every row it appends, and it writes a header for any column it does not find.
> If the grid stops at 19 there is nowhere to put it, and Google rejects the
> whole write:
>
> ```
> Range (Worktime!T1) exceeds grid limits. Max rows: 947, max columns: 19
> ```
>
> Column T is the twentieth. Nothing is written at all — not a partial row.
> The log prints the spreadsheet URL alongside the worksheet name: widen *that*
> document's tab. A tab of the same name in another spreadsheet is a common
> place for the fix to land without effect.
> A new Google Sheet is 26 columns wide by default, so this only bites a sheet
> that was trimmed to fit the header row exactly. Right-click any column header
> and insert a few spare ones; the extra empties are harmless.

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

### From the card

The footer's **Export to Sheets** link opens a dialog with the same two controls,
so neither the range nor the resend needs a service call. **This month**,
**Last month** and **Everything** fill the from-date for you; it opens on the
start of last month, which covers both the month that just closed and the one in
progress. Watch that field — a from-date later than the month you are missing is
the quiet way to export nothing useful, and the run will report success.

Tick **Re-send days already marked as pushed** when the rows are missing from
the sheet even though the integration thinks it sent them. That is the one case
a plain export cannot fix on its own: each day carries a fingerprint of what was
last pushed, and a day whose fingerprint still matches is skipped without a
second thought. If the sheet lost those rows — a cleared tab, a deleted range, a
push that was recorded but never arrived — the fingerprint is a lie no amount of
re-running will notice. Forcing ignores it.

---

## When rows do not appear

Check **Settings → System → Logs** for:

```
Worktime: google_sheets not installed — skipping export
```

That means the Google Sheets integration is missing or the Config Entry ID is
wrong. More symptoms in [Troubleshooting](troubleshooting.md).

A rejection from Google now carries its own reason:

```
Worktime: Sheets append failed for 2026-08-05 (worksheet 'Worktime'):
  {'code': 400, 'message': 'Range (Worktime!T1) exceeds grid limits.
  Max rows: 947, max columns: 19', 'status': 'INVALID_ARGUMENT'}
```

`exceeds grid limits` means the worksheet is too narrow — see
[Columns](#columns). A `403` is a permission or token problem, a `404` a wrong
spreadsheet or worksheet name, and a `429` is quota, which resolves on its own.

Once five days in a row fail the export stops rather than working through the
rest, since a rejection of this kind applies to every remaining day equally:

```
Worktime: export_all aborted after 5 consecutive failures — the cause is
structural, not per-day.
```

Every run also logs its own tally:

```
Worktime: export_all done — sent=12 skipped=140 failed=0 total=152,
covering 2025-09-02..2026-09-01 (since=none, force=False).
Stored locally: 140 history + 12 leave records.
```

Read it as a diagnosis. The `covering` range is the first thing to check when a
month is missing: if it stops before that month, the days are not in local
storage and no export can send them. `sent=0 skipped=N` with rows missing from the sheet means
the fingerprints are stale — force the resend. `failed=N` means Sheets rejected
the rows, and the lines above it say why. A `total` far lower than the number of
days you expect means the days are not in local storage at all, so there is
nothing to export: re-enter the stretch with
[`set_period`](services.md#set_period) first, then export.
