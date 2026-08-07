# Day types

Not every day is a normal day at the office. Setting a day's type tells the
integration how many hours to credit and how the day should appear in Google
Sheets.

Change a type from the card: tap the row (or the pencil), pick **Type**, save.
Or call [`edit_day`](services.md#edit_day) directly.

[← Back to README](../README.md)

---

## The eight types

| Type | Hours credited by default | Notes |
|---|---|---|
| `normal` | Measured from arrival to departure | The default. Nothing to set. |
| `home` | A full net workday | Worked from home. No GPS involved. |
| `sick` | A full net workday | Pass `hours` for a partial day |
| `vacation` | A full net workday | Paid leave. Lunch recorded as "no". |
| `red_day` | A full net workday | Public holiday. Lunch recorded as "no". |
| `squeeze_day` | A full net workday | Bridge day (*klämdag*). Lunch recorded as "no". |
| `off` | `0` | Unpaid day off. Does not count toward overtime. |
| `flex` | `0` | Flex leave. You must state the hours — see below. |

"A full net workday" means your configured workday length minus the lunch
deduction — 8 hours with the defaults. Override it on any type by passing
`hours`, which is how you record a half day:

```yaml
action: worktime_tracker.edit_day
data:
  date: "2026-08-11"
  type: sick
  hours: 4
```

---

## Why flex defaults to zero

The five paid-leave types represent a whole day away from work where you are
still on the clock, so defaulting them to a full day is almost always right.

Flex is different — it is an explicit credit or debit against banked overtime,
and there is no sensible default for "how much". So it records `0` until you say
otherwise, rather than silently crediting a day you did not intend.

---

## Splitting a day

Worked the morning and took flex in the afternoon? That is one day with two
halves, not two days. Use the top-up fields:

```yaml
action: worktime_tracker.edit_day
data:
  date: "2026-08-11"
  arrival: "08:00"
  departure: "12:00"
  top_up_type: flex
  top_up_hours: 4
```

The worked portion is measured from arrival and departure as usual; the top-up
adds its hours on top. Any type works as a top-up. `off` is the exception — it
represents unpaid leave and credits nothing, so it tops up by zero.

Clear a top-up by setting `top_up_type` to an empty string.

---

## A whole stretch of days

For a vacation week or a longer sick leave, use
[`set_period`](services.md#set_period) instead of editing days one at a time:

```yaml
action: worktime_tracker.set_period
data:
  start_date: "2026-07-06"
  end_date: "2026-07-24"
  type: vacation
  skip_existing: true
```

`skip_existing: true` leaves any day that already has data alone, so normal
workdays that fall inside the range are not overwritten.

---

## How types reach Google Sheets

Each row carries a `Type` column — `Normal`, `Sick`, `Off`, `Flex` and so on.
Vacation, public holidays and bridge days also record `Lunch: no`, since you
were not there to take one. Sick and work-from-home days leave lunch unset,
because you may well have taken one either way.
