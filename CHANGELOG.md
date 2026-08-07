# Changelog

All notable changes to Worktime Tracker are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries before 2.1.0 predate this file and are not reconstructed.

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
