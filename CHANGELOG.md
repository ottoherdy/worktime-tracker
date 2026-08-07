# Changelog

All notable changes to Worktime Tracker are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries before 2.1.0 predate this file and are not reconstructed.

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

[2.11.0]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.11.0
[2.10.0]: https://github.com/ottoherdy/worktime-tracker/releases/tag/v2.10.0
