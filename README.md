# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ottoherdy/worktime-tracker?label=release)](https://github.com/ottoherdy/worktime-tracker/releases)

**Your phone is already at work. Let it do the timekeeping.**

Worktime Tracker is a Home Assistant integration that logs when you arrive and
leave work, using the location your phone already reports. It keeps a running
day, week and month total, tracks overtime, handles sick days and vacation, and
can mirror everything to a Google Sheet.

It ships with its own Lovelace card — no other frontend downloads, no manual
resource registration, no template sensors, no YAML automations to copy.

---

## How it works

The integration watches one `person` entity and one Home Assistant zone.

1. **You enter the zone** → arrival is logged
2. **The clock runs continuously** — stepping out for lunch or an errand does
   not stop it
3. **You leave, or press the button** → departure is logged, hours and overtime
   are calculated

That is the whole loop. Everything else — lunch prompts, edits, exports,
different day types — sits on top of it.

---

## Requirements

- Home Assistant 2024.4.0 or newer
- A `person` or `device_tracker` entity with location from a phone
- A [zone](https://www.home-assistant.io/integrations/zone/) covering your workplace
- [HACS](https://hacs.xyz/) for installation
- Optional: the Google Sheets integration, if you want rows in a spreadsheet

---

## Install

**1 — Add the repository to HACS**

HACS → three-dot menu → **Custom repositories** → add
`https://github.com/ottoherdy/worktime-tracker` with category **Integration**.

**2 — Download and restart**

Search for **Worktime Tracker** in HACS, download it, then restart Home Assistant.

**3 — Add the integration**

**Settings → Devices & Services → + Add Integration → Worktime Tracker**

You need to answer two questions to get going — which person to track, and
which zone is work. Everything else has a working default and can be changed
later under **Configure**.

**4 — Put the card on a dashboard**

Add a manual card to any dashboard:

```yaml
type: custom:worktime-tracker-card
```

If the card does not appear, hard-refresh the browser once — the file is new to it.

---

## First day

Nothing to press. Walk into the zone and the card starts counting.

At the configured lunch time (13:00 by default) your phone asks whether you had
lunch, so the deduction is right. At the end of the day, either press **Log
departure** or let the zone exit do it — automatic departure is off until you
turn it on, so start with the button and enable the automation once you trust
the zone.

Got the arrival time slightly wrong? Tap any row in the card to correct it.

---

## Documentation

| Guide | What's in it |
|---|---|
| [Configuration](docs/configuration.md) | Every setting, what it does, and what it defaults to |
| [The card](docs/card.md) | Sections, YAML options, theming, multiple people |
| [Entities](docs/entities.md) | Sensors, attributes, switches and numbers |
| [Services](docs/services.md) | All nine services and their fields |
| [Google Sheets](docs/sheets.md) | Exporting to a spreadsheet, both ways |
| [Day types](docs/day-types.md) | Sick, vacation, flex, work-from-home and the rest |
| [Troubleshooting](docs/troubleshooting.md) | When arrival does not fire and other symptoms |

---

## Features at a glance

- **Automatic arrival and departure** from zone crossings, with a grace window
  so GPS flutter does not end your day early
- **Lunch handling** via a push notification you answer with one tap
- **Eight day types** — normal, sick, off, flex, work-from-home, vacation,
  public holiday and bridge day
- **Edit any day** from the card, including days with no data
- **Weekly and monthly totals** with overtime against a configurable target
- **Google Sheets export**, automatic after departure or on demand, with an
  append-only revision history
- **Arrival and departure margins** so the log matches when you actually start
  working rather than when you cross the geofence
- **Multiple people** in one Home Assistant, each with isolated storage
- **A reminder on Friday** to submit your time report

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions, the release
process, and how to run the integration against a test instance.

Release history is in [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT — see [LICENSE](LICENSE).
