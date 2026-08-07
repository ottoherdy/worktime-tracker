# Entities

Entity IDs carry the instance slug. On the first instance that means
`sensor.today_hours_today`; on an instance named `Person 2` it becomes
`sensor.person_2_today_hours_today`.

[← Back to README](../README.md)

---

## Sensors

| Entity | State | Key attributes |
|---|---|---|
| `sensor.today_hours_today` | Hours worked today, as a float | `arrival`, `departure`, `planned_end`, `lunch`, `human_readable`, `overtime`, `time_remaining`, `status`, `recent_days` (last 60 days) |
| `sensor.today_status` | `off_duty` / `at_work` / `overtime` / `done` | — |
| `sensor.this_week_hours_this_week` | Total hours this ISO week | `hours`, `overtime`, `weekly_target`, `days` |
| `sensor.last_week_hours_last_week` | Total hours last ISO week | `hours`, `overtime`, `days` |
| `sensor.this_month_hours_this_month` | Total hours this calendar month | `hours`, `human_readable`, `overtime`, `month` |
| `sensor.last_month_hours_last_month` | Total hours last calendar month | `hours`, `human_readable`, `overtime`, `month` |

Every entry in a `days` or `recent_days` list has the same shape:

```yaml
date: "2026-04-28"
weekday: Monday
arrival: "08:12"
departure: "16:38"
lunch: "yes"
hours: 8.43
human_readable: "8h 26m"
type: normal
```

The hours sensors update roughly every 30 seconds while you are at work. The
card smooths between ticks, so the display counts up evenly rather than jumping.

---

## Status values

| Status | Meaning |
|---|---|
| `off_duty` | No arrival registered today |
| `at_work` | Arrived, planned end not yet reached |
| `overtime` | Still at work past the planned end |
| `done` | Departure registered |

---

## Binary sensors

| Entity | On when |
|---|---|
| `binary_sensor.today_at_work` | Status is `at_work` or `overtime` |
| `binary_sensor.today_day_complete` | Status is `done` |

---

## Switch

| Entity | What it does |
|---|---|
| `switch.today_auto_departure` | Turns zone-exit departure on and off without opening the config dialog |

---

## Numbers

| Entity | Range | What it does |
|---|---|---|
| `number.today_arrival_margin` | 0–60 min | Minutes added to a GPS arrival. `0` disables. |
| `number.today_departure_margin` | 0–60 min | Minutes subtracted from a GPS departure. `0` disables. |

Manual button presses ignore both margins and log the exact time.

---

## Using these in automations

The attributes are the useful part. To notify when overtime passes an hour:

```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.today_hours_today
    attribute: overtime
    above: 1
action:
  - service: notify.mobile_app_your_phone
    data:
      message: >
        {{ state_attr('sensor.today_hours_today', 'human_readable') }} today —
        time to go home.
```
