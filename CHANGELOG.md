# Changelog

All notable changes to Worktime Tracker are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries before 2.1.0 predate this file and are not reconstructed.

## [2.14.4] — 2026-09-01

### Fixed
- The `export_all` tally could not answer the question people actually bring to
  it. `total=152` says how many days the run considered, but not which days, so
  "month X is missing from the sheet" stayed ambiguous between a day that was
  skipped, a day that failed, and a day that was never in local storage at all.
  The line now prints the date range it covered, the `since` and `force` it ran
  with, and the size of local storage.
- An entry that could not be parsed into a row counted as a failure but did not
  count toward the consecutive-failure abort, so a run could grind through a
  whole year of them one warning at a time.

## [2.14.3] — 2026-08-31

### Fixed
- Sheets failures named the worksheet but not the spreadsheet, which leaves the
  obvious question open when the fix is "go and widen that tab" — there is more
  than one document a tab called `Worktime` could live in. Both the per-day
  warning and the `export_all` abort now name the spreadsheet the config entry
  points at and print its URL, so the tab to edit is one click away.

## [2.14.2] — 2026-08-31

### Fixed
- The `export_all` abort told you to go and read the warning above it. Home
  Assistant's error panel shows that abort on its own, so the reason was one
  log level and several screens away from the line that announced the problem.
  The abort now quotes the rejection Sheets actually returned, and names the
  worksheet it was writing to.

## [2.14.1] — 2026-08-31

### Fixed
- A failed Sheets append said only `Failed to write data`. Home Assistant's
  `google_sheets` integration wraps every underlying API error in that one
  string, and the cause — which carries the status code and Google's own
  message — was dropped on the floor. The warning now names the worksheet and
  the chained cause, so a too-narrow sheet, a revoked token and a quota
  rejection stop looking identical.
- `export_all` worked through every remaining day after a structural failure,
  turning one misconfiguration into one warning per day. It now stops after
  five consecutive failures and says why.
- `export_all` sent its appends as fast as it could manage. The Sheets API
  allows 60 writes per minute, so a forced export of a long range spent its
  tail being rejected for quota. Appends are now paced.

### Documentation
- The column table listed 15 columns; the integration writes 19. `Week`,
  `Month`, `Top-up type` and `Top-up hours` were missing. A sheet built to
  match the old table is too narrow to accept a row.
- Documented that the worksheet needs **at least 20 columns**: the 19 written
  here plus the `created` column that `google_sheets` adds to every row. A grid
  that stops at 19 rejects the entire write with `exceeds grid limits`.

## [2.14.0] — 2026-08-31

### Added
- An **Export to Sheets** dialog in the card footer, with a from-date and a
  **Re-send days already marked as pushed** option. Both were reachable only by
  calling `export_all` by hand before. The footer link is now on by default —
  an export button that ships switched off helps nobody.

### Changed
- The footer link no longer fires an unconditional export behind a confirm
  dialog. It opens the range picker instead, defaulting to the first of the
  current month.

### Fixed
- Documented the case the old button could not fix: a day is skipped when its
  fingerprint matches the last push, so rows lost on the Sheets side — a cleared
  tab, a deleted range, a push recorded but never delivered — stayed missing no
  matter how often the export was re-run. The force option ignores fingerprints.
  `docs/sheets.md` now also reads the `sent/skipped/failed/total` log line as a
  diagnosis.

## [2.13.0] — 2026-08-20

### Added
- Days can be booked before they happen. The card's look-up picker no longer
  stops at today, so a week of vacation or sick leave can be entered in advance
  with **Add**, or in one go with `set_period`. A booked day that has not yet
  arrived is marked **Planned** in the look-up box.
- `sensor.this_month_hours_this_month` gained an `upcoming_days` attribute
  listing those pre-booked days, and each entry in the week sensors' `days`
  attribute carries a `planned` flag.

### Fixed
- Leave dated in the future inflated the week and month totals. `set_period`
  already accepted future ranges, and the hours it credited were summed over the
  whole week or calendar month while the matching overtime figure only ever
  built its expected total from days up to today — so booking next week's
  vacation showed up immediately as overtime that had not been worked. Both
  totals now stop at today; planned days start counting on the day they arrive.

## [2.12.1] — 2026-08-07

### Fixed
- Leave days were wiped on every restart. `_async_save` wrote the HA store
  version into the payload's `schema_version` field, which is always `1`, so the
  v1→v2 migration ran on every load and never converged. That migration rebuilt
  `leave_records` from `history` alone, keeping only sick days — so vacation,
  off, flex, work-from-home, red days and squeeze days were discarded each time,
  and sick days went with them on the following restart.

  The migration now merges into the existing `leave_records` instead of
  replacing it, carries over every key it does not touch, and the saved
  `schema_version` is a real schema constant, so it runs once and stops.
- Arrival and departure margins, and the Google Sheets sync fingerprints, were
  dropped by the same migration. Both are preserved now.

> Days already lost cannot be recovered — they are gone from storage. Re-enter a
> stretch with `worktime_tracker.set_period`, then run
> `worktime_tracker.export_all` to bring Google Sheets back in line.

## [2.12.0] — 2026-08-07

### Added
- `clear_day` now appears in the Home Assistant UI with a name, description and
  date picker. It was registered in code but missing from `services.yaml`, so it
  could only be called by the card or from YAML.
- Every service now offers the `entry_prefix` field in the UI. All nine accepted
  it already, but five did not declare it — which is exactly the field you need
  on a multi-instance setup.

### Fixed
- Service translations listed `export_history`, which does not exist, and were
  missing four services that do. All nine are now present in English and Swedish.

### Changed
- Documentation split up. The README is now a short introduction and install
  guide; the reference material moved to `docs/` — configuration, the card,
  entities, services, day types, Google Sheets and troubleshooting.
- Documented the four day types that were never written down (`home`,
  `vacation`, `red_day`, `squeeze_day`), the `set_period` service, day splitting
  via top-up, and the six configuration settings added since 2.9.0.
- Releases are now published automatically when the manifest version changes, so
  HACS shows an update with the changelog section as its notes.
- Commit messages follow Conventional Commits, enforced in CI. See
  `CONTRIBUTING.md`.

## [2.11.0] — 2026-07-30

### Added
- Day split via top-up: a workday can be topped up from a second period.

### Changed
- Flex time now counts against overtime rather than being tracked separately.

## [2.10.0] — 2026-07-30

### Added
- Back navigation on the week and month blocks, so previous periods can be browsed.
- Vacation as a distinct day type.
- Period modal for reviewing a selected week or month.
- `red_day` and `squeeze_day` day types; leave days now record lunch as "no".
- Average arrival and departure time shown on the month blocks.

### Fixed
- The card falls back to legacy entity IDs when an entity prefix does not resolve.
- Clearer hint for the Entity prefix field in the visual editor.

## [2.9.8] — 2026-06-09

### Changed
- Removed hardcoded personal names from defaults.

### Fixed
- The card warns when its entity prefix is missing instead of rendering empty.

## [2.9.7] — 2026-06-09

### Fixed
- Hours are no longer pre-filled when editing an ordinary day.

## [2.9.6] — 2026-06-09

### Fixed
- Service calls without `entry_prefix` no longer overwrite data belonging to another instance.

## [2.9.5] — 2026-06-07

### Changed
- Empty off-day rows are hidden in the week tables.

## [2.9.4] — 2026-06-07

### Added
- Configurable work days.
- Confirmation prompt when arriving on a day marked as off.
- Seven-day week view.

## [2.9.3] — 2026-06-07

### Added
- `clear_day` service and a Clear day button on the card.

### Fixed
- `edit_day` hour overrides now apply on normal edits.
- Flex defaults to 0.

## [2.9.2] — 2026-06-03

### Fixed
- Zone exits are debounced with a grace window, so GPS flutter no longer triggers departure.

## [2.9.1] — 2026-06-03

### Fixed
- Notification actions are scoped per instance.

## [2.9.0] — 2026-06-01

### Added
- Work-from-home day type.
- Dropdown for picking the notify service in the config flow.
- Morning reminder and forgot-departure reminder.

## [2.8.4] — 2026-06-01

### Changed
- The card extrapolates elapsed time between the 30-second sensor ticks, so the
  running total updates smoothly.

## [2.8.3] — 2026-05-30

### Fixed
- Zone detection works for zones whose friendly name differs from the slug,
  including multi-word zone names.

## [2.8.2] — 2026-05-30

### Added
- Add-via-lookup for instances with no data yet.

### Fixed
- Editor no longer loses input focus while typing.

## [2.8.0] — 2026-05-30

### Added
- `export_all` service, to catch Google Sheets up on missing or changed days.

## [2.7.3] — 2026-05-29

### Added
- Weekly total hours in the section headers.

## [2.7.2] — 2026-05-28

### Added
- Weekly overtime in the section headers.

## [2.7.1] — 2026-05-28

### Fixed
- The card JS URL is cache-busted, so updates take effect without a hard refresh.

## [2.7.0] — 2026-05-27

### Added
- Easy-edit options in the visual editor.

## [2.6.0] — 2026-05-27

### Changed
- Orange accent colour and general layout polish.

## [2.5.2] — 2026-05-27

### Fixed
- Per-entry storage, so multiple instances no longer share the same data.

## [2.5.1] — 2026-05-27

### Fixed
- Multi-instance entity mapping.

## [2.5.0] — 2026-05-27

### Added
- Dark mode.
- Look-up box.
- Flex day type.

## [2.4.3] — 2026-05-27

### Added
- `max_width` card option for a wider or fluid layout.

## [2.4.2] — 2026-05-27

### Fixed
- The edit modal pauses re-renders while it is open.

## [2.4.1] — 2026-05-27

### Changed
- Card polish.

## [2.4.0] — 2026-05-27

### Added
- Month sections.
- Multi-instance support.

### Changed
- Card refinements.

## [2.3.0] — 2026-05-27

### Changed
- Phone-first card redesign.

## [2.2.0] — 2026-05-27

### Added
- Week tables.
- Edit pencil.
- Visual editor for the card.
- CSS custom properties for theming.

## [2.1.0] — 2026-05-27

### Added
- Arrival and departure margins.
- Inline editing on the card.
- The card is auto-loaded by the integration — no manual resource registration.

[2.12.1]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.12.1
[2.12.0]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.12.0
[2.11.0]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.11.0
[2.10.0]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.10.0
