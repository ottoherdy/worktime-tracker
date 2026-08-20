# Services

Nine services, callable from **Developer Tools → Actions**, automations, scripts
or the card.

Every one of them accepts an optional **`entry_prefix`**. Leave it out on a
single-instance setup. On a multi-instance setup it restricts the call to one
instance — the card fills it in automatically from its own `entity_prefix`.
Omitting it means every instance responds.

[← Back to README](../README.md)

---

## Registering time

### `log_arrival`

Registers arrival right now. Manual, so the arrival margin does not apply.

### `log_departure`

Registers departure right now. Manual, so the departure margin does not apply.

### `set_lunch`

| Field | Type | Default |
|---|---|---|
| `had_lunch` | boolean | `true` |

Sets whether lunch was taken. `false` subtracts the lunch deduction.

### `reset_today`

Clears today's registrations so you can start over. Today only.

---

## Editing history

### `edit_day`

Edits or creates any day, past or present.

| Field | Type | Notes |
|---|---|---|
| `date` | date | Defaults to today |
| `type` | select | One of the [eight day types](day-types.md) |
| `arrival` | time | |
| `departure` | time | |
| `lunch` | select | `yes` / `no` / `unknown` |
| `hours` | float | Overrides the calculated hours |
| `top_up_type` | select | Splits the day — see [splitting a day](day-types.md#splitting-a-day) |
| `top_up_hours` | float | Hours credited for the top-up |

All fields are optional. The updated row goes to Sheets marked `Edited: yes`
with `Rev` incremented.

```yaml
action: worktime_tracker.edit_day
data:
  date: "2026-08-04"
  arrival: "08:15"
  departure: "16:45"
  lunch: "yes"
```

### `clear_day`

| Field | Type | Notes |
|---|---|---|
| `date` | date | Defaults to today |

Wipes the day completely — history and leave entries both. If the date is today,
the live arrival, departure and lunch state resets too.

> Any row already written to Google Sheets stays there. Clearing is local only;
> tidy the sheet by hand if you need to.

### `set_period`

Applies one type across a date range, looping `edit_day` over each day. The
range may lie in the future — this is the intended way to book a week of
vacation or sick leave ahead of time. Days you have booked but not yet reached
are held out of the week and month totals until they arrive; see
[Booking days ahead](card.md#booking-days-ahead).

| Field | Type | Required | Notes |
|---|---|---|---|
| `start_date` | date | yes | |
| `end_date` | date | yes | Inclusive |
| `type` | select | yes | One of the [eight day types](day-types.md) |
| `hours` | float | no | Per-day hours override |
| `skip_existing` | boolean | no | Default `false`. `true` leaves days that already have data alone. |

```yaml
action: worktime_tracker.set_period
data:
  start_date: "2026-07-06"
  end_date: "2026-07-24"
  type: vacation
  skip_existing: true
```

---

## Google Sheets

### `export_today`

Sends today's row to the configured worksheet immediately, without waiting for
the auto-export delay.

### `export_all`

Walks the full local history and re-sends every day that is either missing from
the sheet or has changed since it was last pushed. Unchanged days are skipped —
each row is fingerprinted with SHA-256 — so running it repeatedly is cheap.

| Field | Type | Notes |
|---|---|---|
| `since` | ISO date | Only consider days on or after this date |
| `force` | boolean | Default `false`. `true` re-sends even unchanged days. |

Useful when:

- You have just set up Sheets on an instance that already has history
- You bulk-edited days locally and want the sheet caught up
- You are moving data to a different sheet

```yaml
action: worktime_tracker.export_all
data:
  since: "2026-01-01"
```

The card's optional **Export all** footer link calls this behind a confirmation
dialog. Enable it with `show_btn_export_all: true`.
