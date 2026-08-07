# Configuration

Everything here is set through the UI — **Settings → Devices & Services →
Worktime Tracker → Configure**. Nothing needs to go in `configuration.yaml`.

Only **Person entity** and **Work zone** have no useful default. The rest can
stay as they are until you have a reason to change them.

[← Back to README](../README.md)

---

## Core

| Setting | Default | What it does |
|---|---|---|
| Instance name | `Worktime Tracker` | Used as the slug for entity IDs and service routing. Set something distinct (`Person 1`, `Person 2`) if you add a second instance — see [multiple people](card.md#multiple-people). |
| Person entity | — | The `person.*` or `device_tracker.*` to follow |
| Work zone | — | The zone that counts as "at work" |
| Work days | Mon–Fri | Which weekdays count toward the weekly target. Arriving on a non-work day asks for confirmation first. |
| Workday length | `8.5 h` | A full workday **including** the lunch break |
| Lunch deduction | `0.5 h` | Subtracted when lunch is answered "yes" |
| Weekly target | `40 h` | Used for the weekly overtime figure |

> **Gross versus net.** Workday length is gross. With the defaults, a day with
> lunch nets 8 hours of work; a day without lunch nets 8.5.

---

## Arrival and departure

| Setting | Default | What it does |
|---|---|---|
| Auto departure | Off | Whether leaving the zone can end your day |
| Auto departure time | `15:00` | Zone exits before this are ignored, so a lunch run does not clock you out. Exits at or after it trigger departure. |
| Zone exit grace | `5 min` | How long you must stay outside the zone before it counts as leaving. Absorbs GPS flutter. |

Zone matching uses the zone's **friendly name**, which is what Home Assistant
actually stores in `person.*` state — so a zone called `My Office` works exactly
like a single-word one.

Two more values live on the device page as `number` entities rather than in this
dialog, because they are worth adjusting on the fly:

| Entity | Default | What it does |
|---|---|---|
| `number.today_arrival_margin` | `0 min` | Minutes **added** to a GPS arrival. Set `3` and a 07:00 zone entry is logged as 07:03. |
| `number.today_departure_margin` | `0 min` | Minutes **subtracted** from a GPS departure. Set `3` and a 17:00 exit is logged as 16:57. |

Both are for the walk between the geofence edge and your desk. Manual button
presses log the exact time and ignore them.

---

## Notifications

| Setting | Default | What it does |
|---|---|---|
| Notify service | — | Your mobile app service, **without** the `notify.` prefix — e.g. `mobile_app_your_phone` |
| Lunch check time | `13:00` | When the lunch question is sent |
| Assume lunch if no answer | On | At departure with no reply, assume lunch was taken |
| Morning reminder | Off | A nudge if you have not arrived yet |
| Morning reminder time | `09:30` | When that nudge is sent |
| Forgot-departure reminder | Off | Asks whether you left, when you are still counted as at work |
| Forgot-departure offset | `30 min` | How long past your planned end to wait before asking |

Leave the notify service empty to switch off every notification, including the
Friday time-report reminder.

---

## Google Sheets

| Setting | Default | What it does |
|---|---|---|
| Auto export to Sheets | On | Send the day automatically after departure |
| Auto export delay | `3 h` | How long to wait, so you have time to fix mistakes first |
| Google Sheets config entry | — | The Config Entry ID of your Google Sheets integration |
| Sheets worksheet | `Worktime` | Which worksheet (tab) to write to |

Full setup, including the column layout, is in [Google Sheets](sheets.md).

---

## Changing settings later

Everything above can be changed at any time under **Configure** on the
integration card. Changes take effect immediately, with one exception: if you
edit an arrival time, reload the integration for the planned end time to
recalculate.

## Multiple instances

Add the integration more than once to track more than one person. Give each a
distinct instance name — entity IDs are derived from it, and each instance gets
its own isolated storage file, so histories never bleed into each other.

See [multiple people](card.md#multiple-people) for pointing a card at a
specific instance.
