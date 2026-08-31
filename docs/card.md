# The card

The integration registers its own Lovelace card and serves the file itself.
There is nothing to download and no resource to register:

```yaml
type: custom:worktime-tracker-card
```

It is capped at 420 px wide by default — built for a phone first, but it renders
cleanly on a desktop dashboard too. If it does not show up right after
installing, hard-refresh the browser once.

[← Back to README](../README.md)

---

## What's on it

Top to bottom, with the defaults:

| Section | Shown | Contents |
|---|---|---|
| Topbar | off | Today's date, centered |
| Today | on | Big elapsed time, target sub-line, progress bar, In / Out / Lunch strip, action buttons, and an "On the clock" pulse while running |
| This week | on | One row per work day with arrival → departure and hours, today highlighted, totals in the footer |
| Last week | on | Same layout |
| This month | off | Total hours and overtime |
| Last month | off | Same |
| History | on | Compact list with a bar per day, turning warn-orange past the daily target |
| Look up day | on | Date picker reaching any day, past or future — **Edit** opens it filled in, **Add** opens a blank day |
| Footer | on | "Saved locally" on the left, Add period / Export / Sheets / Export to Sheets on the right |

Tap any row, or the pencil, to open the edit modal for that day. **Reset today**
asks for confirmation first.

### Booking days ahead

The look-up picker accepts future dates, so a week of vacation or a stretch of
sick leave can be entered before it happens. Pick the day, press **Add**, choose
the type, save. For a run of days use the period dialog (or
[`set_period`](services.md#set_period)) instead of one day at a time.

A day you have booked but not yet reached is marked **Planned** in the look-up
box. Planned days stay out of the This week / This month totals and out of the
overtime figures until the day actually arrives — otherwise next week's booked
vacation would read as hours already worked. They are stored, exported to Google
Sheets, and editable the whole time; they simply start counting on the day.

---

## Visual editor

Click the card in dashboard edit mode. Everything below is available there —
section toggles, button toggles, label rewrites, colours, theme, font scale,
padding, corner radius, width and time format. Text fields keep focus while you
type.

---

## YAML options

All optional.

```yaml
type: custom:worktime-tracker-card

# Sections
show_topbar: false           # centered date
show_today: true             # elapsed time and actions
show_this_week: true
show_last_week: true
show_this_month: false
show_last_month: false
show_history: true
show_lookup: true            # look up / add day picker
show_footer: true
show_edit: true              # pencil and row-tap → modal

# Buttons inside the Today card
show_btn_arrival: true
show_btn_reset: true
show_btn_departure: true
show_btn_lunch: true
show_btn_auto: true
show_btn_export_all: true    # "Export to Sheets" dialog link in the footer

# Size and layout
padding: 14                  # outer padding, pixels
corner_radius: 16
max_width: 420               # 0 for fluid
font_scale: "M"              # S / M / L
compact: false

# Theme and colour
theme: "auto"                # auto / light / dark
color_preset: "orange"       # orange / blue / green / purple / slate
color_bg: ""                 # custom hex, overrides the preset
color_card: ""
color_ink: ""
color_accent: ""
color_warn: ""

# Section titles
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

# Multiple people
entity_prefix: ""            # instance slug — see below
```

---

## Multiple people

The integration accepts more than one config entry, each with its own instance
name and its own isolated storage.

A card with no `entity_prefix` reads the original instance
(`sensor.today_hours_today`). To bind a card to another instance, set
`entity_prefix` to that instance's slug:

| Instance name | `entity_prefix` |
|---|---|
| `Person 2` | `person_2` |
| `Worktime Tracker Person 1` | `worktime_tracker_person_1` |

The card then reads `sensor.<prefix>_today_hours_today` and stamps its service
calls with the prefix, so only the matching instance responds.

If a button does nothing on a multi-instance setup, check **Settings → System →
Logs** for a line like `Worktime: edit_day for … matched no instance` — it lists
the active slugs, so you can see what to put in `entity_prefix`.

---

## Theming

Every visual token is a CSS variable on `:host`. Override them in a theme, with
`card_mod`, or through the visual editor's colour fields:

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

Available: `--wt-bg`, `--wt-paper`, `--wt-card`, `--wt-ink`, `--wt-ink-2`,
`--wt-muted`, `--wt-muted-2`, `--wt-line`, `--wt-line-2`, `--wt-accent`,
`--wt-accent-soft`, `--wt-good`, `--wt-warn`, `--wt-danger`.

---

## The legacy dashboard

`dashboards/dashboard.yaml` is an older hand-built view kept for reference. It
needs the [Mushroom](https://github.com/piitaya/lovelace-mushroom) card
collection from HACS and assumes default entity IDs. The bundled card above is
the maintained option.
