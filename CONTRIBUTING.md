# Contributing

Thanks for taking a look. Issues and pull requests are both welcome.

## Reporting a problem

Open an [issue](https://github.com/ottoherdy/worktime-tracker/issues) and include:

- Your Home Assistant version and the Worktime Tracker version (Settings → Devices & Services → Worktime Tracker)
- What you expected versus what happened
- Relevant log output

Turn on debug logging by adding this to `configuration.yaml` and restarting:

```yaml
logger:
  logs:
    custom_components.worktime_tracker: debug
```

Most arrival and departure problems show up there as state-change events, which
makes them far quicker to diagnose than a description alone.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
CI checks the format on every push and pull request, and fails on anything that
does not match:

```
<type>[optional scope][!]: <description>
```

| Type | Use for |
|---|---|
| `feat` | A new capability users can see |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system or dependencies |
| `ci` | CI configuration and workflows |
| `chore` | Housekeeping that does not touch `custom_components/` behaviour |
| `style` | Formatting only |
| `revert` | Reverting an earlier commit |

Useful scopes in this repo: `card`, `coordinator`, `config-flow`, `sheets`,
`sensor`, `docs`.

```
feat(card): add a month summary section
fix: stop zone flutter from logging an early departure
docs: explain the multi-instance entity prefix
feat(coordinator)!: store lunch deduction per entry
```

Append `!` after the type or scope for a breaking change, and explain the break
in the commit body.

Only new commits are checked — history predating the rule is left alone. If CI
rejects a message, reword it with `git commit --amend` (or
`git rebase -i` for something further back) and force-push the branch.

## Releasing

Releases are automatic. Everything keys off the version in the manifest:

1. Bump `version` in `custom_components/worktime_tracker/manifest.json`
2. Add the matching section to [CHANGELOG.md](CHANGELOG.md), newest first:

   ```markdown
   ## [2.12.0] — 2026-08-14

   ### Added
   - What the user can now do.
   ```

3. Merge to `main`

The release workflow notices the changed version, tags the commit `vX.Y.Z`, and
publishes a GitHub Release using that CHANGELOG section as the notes. HACS reads
GitHub Releases, so this is the step that tells existing users an update exists
and shows them what changed.

Nothing is published if the tag already exists, so re-running is harmless.

**Bump the version for any change that reaches users** — including card-only
changes. The card's URL is cache-busted per version, so shipping card edits
without a bump leaves browsers on the old file.

Version numbers follow [Semantic Versioning](https://semver.org/): breaking
changes bump major, new features bump minor, fixes bump patch.

## Local development

To use the integration, install it through HACS. The steps below are only for
changing it.

`deploy.sh` copies the integration to a Home Assistant host over SSH and
restarts it:

```bash
./deploy.sh                     # host defaults to "homeassistant"
HA_HOST=ha.lan ./deploy.sh      # or point it elsewhere
```

It needs SSH access with `/config` writable and `ha` on `PATH` — the "Advanced
SSH & Web Terminal" add-on provides both.

The card is served from `custom_components/worktime_tracker/www/` and registered
by the integration, so there is no build step. Edit the JavaScript, restart Home
Assistant, and hard-refresh the browser.

## What CI checks

Every push and pull request runs:

| Job | What it does |
|---|---|
| Hassfest validation | Home Assistant's own manifest and structure checks |
| HACS validation | Confirms the repository is installable through HACS |
| Python syntax | `compileall` over the integration |
| JavaScript syntax | `node --check` over the card, widget and Apps Script |
| Commit messages | Conventional Commits format on new commits |

You can run the Python and JavaScript checks locally:

```bash
python -m compileall custom_components/worktime_tracker
node --check custom_components/worktime_tracker/www/worktime-tracker-card.js
```

There is no automated test suite yet. Changes to arrival, departure or rollover
logic are worth exercising against a real instance before merging.
