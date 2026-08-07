# Troubleshooting

Start by turning on debug logging — most of these problems announce themselves
clearly once you can see the state-change events.

```yaml
logger:
  logs:
    custom_components.worktime_tracker: debug
```

Add that to `configuration.yaml`, restart, then watch **Settings → System → Logs**.

[← Back to README](../README.md)

---

## Arrival is not logged automatically

Almost always the zone.

Home Assistant stores the zone's **friendly name** in `person.*` state, not the
entity ID slug. Check what your person entity actually reports in **Developer
Tools → States** and confirm it matches your configured work zone. Multi-word
names like `My Office` are fine.

If the state looks right but nothing fires, the phone may not be reporting
location often enough. Check that the companion app has background location
permission and that the zone is large enough for GPS accuracy at that spot.

## Departure fires too early

Your phone drifted out of the zone. Raise the **zone exit grace** setting — how
long you must be outside before it counts — and confirm the **auto departure
time** is after any lunch trip.

If it keeps happening, turn auto departure off and use the button. The switch
`switch.today_auto_departure` toggles it from the dashboard.

## Departure never fires

Auto departure is off by default. Turn it on in the configuration, or via
`switch.today_auto_departure`.

If it is on and still nothing happens, check that you leave the zone at or after
the configured auto-departure time — exits before it are ignored on purpose.

Enable the **forgot-departure reminder** to get asked instead of silently losing
the day. Unclosed days are finalised at the 03:00 rollover and marked
`Punch-out missing: yes`, so they can be corrected from the card afterwards.

## The lunch notification never arrives

The notify service must be entered **without** the `notify.` prefix —
`mobile_app_your_phone`, not `notify.mobile_app_your_phone`.

An empty notify service disables every notification, including the Friday
reminder.

## Rows do not appear in Google Sheets

Look for this in the log:

```
Worktime: google_sheets not installed — skipping export
```

If it is there, the Google Sheets integration is not installed or the Config
Entry ID is wrong. See [Google Sheets](sheets.md).

Remember that auto-export waits for the configured delay after departure — three
hours by default. Call `worktime_tracker.export_today` if you want the row now.

## The Hours column shows dates

Format the `Hours` and `Overtime` columns in Google Sheets as **Number** rather
than Automatic. Left on Automatic, Sheets interprets `8.43` as a date.

## Card buttons do nothing

On a setup with more than one instance, look for:

```
Worktime: edit_day for … matched no instance — Active slugs: [...]
```

The log line lists the active slugs. Set the card's `entity_prefix` to one of
them — see [multiple people](card.md#multiple-people).

## The card does not appear at all

Hard-refresh the browser. The card file is served by the integration and the
browser has not seen it before.

After an update, the URL is cache-busted per version, so a normal refresh is
enough — as long as the version was bumped. A card change shipped without a
version bump will leave browsers on the old file.

## Planned end time is wrong after editing arrival

Reload the integration. **Settings → Devices & Services → Worktime Tracker →
three-dot menu → Reload.**

## Something else

Open an [issue](https://github.com/ottoherdy/worktime-tracker/issues) with your
Home Assistant version, the integration version, and the relevant log output.
