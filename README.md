# TimePoll

Django + Vue.js polling app for scheduling meetings with multilingual UI (`en`, `fi`, `sv`, `no`, `et`).

## Requirements

- Python 3.13+

## Quick start

Create the virtualenv and install development dependencies:

```bash
python3.13 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
```

Set the required environment variables:

```bash
export TIMEPOLL_SECRET_KEY='dev-only-secret-change-me'
export TIMEPOLL_DEBUG='1'
export TIMEPOLL_ALLOWED_HOSTS='127.0.0.1,localhost'
# Optional: Python-level audit guard
# export TIMEPOLL_AUDIT_GUARD_MODE='off'
# export TIMEPOLL_AUDIT_NETWORK_MODE='log'
# export TIMEPOLL_AUDIT_PROCESS_MODE='off'
# export TIMEPOLL_AUDIT_FILE_MODE='off'
# export TIMEPOLL_AUDIT_SQLITE_MODE='off'
# export TIMEPOLL_AUDIT_ALLOWLIST=''
# export TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST="$PWD,$PWD/venv"
# export TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST="$PWD/db.sqlite3,/tmp"
# export TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST="$PWD/db.sqlite3,:memory:,sqlite-memory-prefix:memorydb_"
```

Apply migrations and start the development server:

```bash
./venv/bin/python manage.py migrate
./venv/bin/python manage.py runserver
```

Open the app at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

Optional browser test setup:

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.playwright-browsers" ./venv/bin/python -m playwright install chromium
```

## Toolforge

If you deploy this app on Toolforge using the Build Service, prefer running the webservice without the shared NFS mount unless the tool explicitly needs files from `$HOME`.

Start the webservice once with no shared storage mount:

```bash
toolforge webservice buildservice start --mount=none
```

To make the same setting persistent, add it to `$HOME/service.template`:

```yaml
type: buildservice
mount: none
```

Use `mount: all` only when the tool truly needs Toolforge shared storage. Running with `mount: none` reduces the writable filesystem surface inside the pod and is the preferred default for this project.

Optional Python-level audit guard:

- `TIMEPOLL_AUDIT_GUARD_MODE` sets the default mode for all guard domains: `off`, `log`, or `enforce`.
- `TIMEPOLL_AUDIT_NETWORK_MODE` overrides the network guard mode per domain.
- `TIMEPOLL_AUDIT_PROCESS_MODE` overrides the subprocess/exec guard mode per domain. When enabled, it blocks all Python-launched subprocess and exec events; this project does not support a subprocess allowlist.
- `TIMEPOLL_AUDIT_FILE_MODE` overrides the file-open guard mode per domain.
- `TIMEPOLL_AUDIT_SQLITE_MODE` overrides the SQLite guard mode per domain.
- `TIMEPOLL_AUDIT_ALLOWLIST` accepts comma-separated network hosts or `host:port` rules. In `enforce` mode, startup rejects any external hosts, so loopback destinations must be listed explicitly if you want to allow them.
- `TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST` accepts comma-separated path prefixes allowed for file reads.
- `TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST` accepts comma-separated path prefixes allowed for file writes.
- `TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST` accepts comma-separated SQLite database paths, exact SQLite URI literals, `:memory:`, or explicit shared-memory URI prefixes such as `sqlite-memory-prefix:memorydb_` (which match `file:memorydb_...?mode=memory` style URIs).

Start with `log` mode before enabling `enforce`, especially for file access. Importing Python modules, reading templates, and opening the SQLite database will all trigger audit events. This guard is useful as a tripwire and fail-fast mechanism, but it is not a real sandbox. Keep infrastructure-level controls such as Toolforge `mount: none`, CSP, and any supported network-layer restrictions as the primary security boundary.

## Commands

Canonical project commands live in `tools/`. `Makefile` is optional and only provides shortcuts for them.

Core workflow:

```bash
sh tools/dev.sh
sh tools/test-backend.sh
sh tools/test-backend-guard.sh
sh tools/test-backend-file-watch.sh
sh tools/test-backend-file-enforce-smoke.sh
sh tools/quality-core.sh
```

Browser and full quality workflow:

```bash
sh tools/install-browser.sh
sh tools/test-browser.sh
sh tools/test-browser-storyboard.sh
sh tools/quality-full.sh
sh tools/pre-push.sh
```

Optional storyboard workflow e2e checks:

```bash
sh tools/test-browser-storyboard.sh
```

Optional `make` shortcuts:

```bash
make dev
make test
make test-guard
make test-file-watch
make test-file-enforce-smoke
make quality
make test-browser
make test-browser-storyboard
make quality-full
make pre-push
```

## Features

- Vue.js frontend with static assets under `polls/static/`
- JSON API backend in Django for fast interactions (no full-page reload required)
- Poll lifecycle:
  - Create poll from full start/end days (slots are always 60 minutes) (requires login)
  - Limit poll slots by daily start/end hour, selected weekdays, and poll timezone
  - Automatic slot grid generation
  - Optional poll identifier (`A-Z`, `a-z`, `0-9`, `_`) to use in links instead of random UUID
  - Vote/edit on each slot with `yes`, `no`, `maybe`, or empty (no value) (requires login)
  - Close poll (creator only)
  - Delete poll only after close (creator only)
- Authentication with name + PIN (login auto-creates new user if name does not exist)
- Session-based login state
- Mobile-friendly and accessibility-focused UI

## Tests

Backend and core quality:

```bash
sh tools/test-backend.sh
sh tools/test-backend-guard.sh
sh tools/test-backend-file-watch.sh
sh tools/test-backend-file-enforce-smoke.sh
sh tools/quality-core.sh
```

`sh tools/test-backend-guard.sh` enables the ready-made audit-guard test profile:

- network guard: `enforce`
- process guard: `enforce`
- SQLite guard: `enforce`
- file guard: `off` by default to avoid noisy import/template access during normal backend tests

You can still override any individual guard variable when needed, for example:

```bash
TIMEPOLL_AUDIT_FILE_MODE=log sh tools/test-backend-guard.sh
```

`sh tools/test-backend-file-watch.sh` is a stricter visibility profile for file access:

- network guard: `enforce`
- process guard: `enforce`
- SQLite guard: `enforce`
- file guard: `log`

Use it when you want backend tests to surface unexpected file reads and writes without immediately failing the whole suite on first sighting.

`sh tools/test-backend-file-enforce-smoke.sh` is the CI smoke profile for file enforcement:

- network guard: `enforce`
- process guard: `enforce`
- file guard: `enforce`
- SQLite guard: `enforce`
- `PYTHONDONTWRITEBYTECODE=1` to avoid `.pyc` writes during the smoke run
- scoped to `polls.tests.SecurityHeaderTests` and `polls.test_runtime_guard.RuntimeAuditGuardTests`

This profile is intentionally small and stable. It is meant to prove that startup, imports, and a representative smoke slice stay inside the file allowlist under `enforce`, without making the full backend suite too brittle for CI.

Browser and full quality:

```bash
sh tools/install-browser.sh
sh tools/test-browser.sh
sh tools/test-browser-storyboard.sh
sh tools/quality-full.sh
sh tools/pre-push.sh
```

`sh tools/pre-push.sh` adds the stricter pre-push checks on top of the normal full quality run by also executing the full backend audit-guard profile and the file-enforcement smoke suite before the browser suites.

`pytest` remains available for backend-only collection:

```bash
sh tools/pytest.sh
```

Optional custom poll link format:

- `http://127.0.0.1:8000/?id=Poll_Name_2026`

## CI merge gates

This repository includes GitHub Actions checks in `.github/workflows/ci.yml`:

- `sh tools/quality-core.sh`
- `sh tools/install-browser.sh`
- `sh tools/test-browser.sh`
- `sh tools/test-browser-storyboard.sh`

Note: the `pip-audit` target currently ignores advisory `GHSA-5239-wwwm-4pmq`
for `pygments`, because no fixed upstream release is available yet.

The coverage gate currently requires at least `87%` total Python coverage.

To enforce these checks as merge gates in GitHub:

1. Enable branch protection on your default branch.
2. Enable `Require a pull request before merging`.
3. Enable `Require review from Code Owners`.
4. Enable `Require status checks to pass before merging` and select `CI / quality`.

## Notes

- Vue app code is in Django static files.
- Frontend logic is split between `polls/static/polls/js/app_logic.js` and `polls/static/polls/js/app.js`.
- The application page loads those two JavaScript files directly without a build step.
- Browser-run JS unit tests live under `polls/static/polls/js/tests/` and are executed via Playwright.
- Browser tests also include the axe accessibility smoke test.
- Vue runtime is loaded from Wikimedia CDN: `https://tools-static.wmflabs.org/cdnjs/...`.
- Required environment variables:
  - `TIMEPOLL_SECRET_KEY`: non-empty secret string
  - `TIMEPOLL_DEBUG`: boolean-like string (`1/0`, `true/false`, `yes/no`, `on/off`)
  - `TIMEPOLL_ALLOWED_HOSTS`: comma-separated hostnames (for example `127.0.0.1,localhost`)
- Optional runtime guard variables:
  - `TIMEPOLL_AUDIT_GUARD_MODE`: default `off`, `log`, or `enforce`
  - `TIMEPOLL_AUDIT_NETWORK_MODE`: per-domain override for network events
  - `TIMEPOLL_AUDIT_PROCESS_MODE`: per-domain override for subprocess and exec events; when enabled, all subprocess and exec launches are blocked
  - `TIMEPOLL_AUDIT_FILE_MODE`: per-domain override for file-open events
  - `TIMEPOLL_AUDIT_SQLITE_MODE`: per-domain override for SQLite connection events
  - `TIMEPOLL_AUDIT_ALLOWLIST`: comma-separated hosts or `host:port` rules; in `enforce` mode, external hosts are rejected at startup and loopback hosts must be listed explicitly
  - `TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST`: comma-separated path prefixes allowed for reads
  - `TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST`: comma-separated path prefixes allowed for writes
  - `TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST`: comma-separated SQLite database paths, exact SQLite URI literals, `:memory:`, or `sqlite-memory-prefix:memorydb_` style shared-memory URI prefixes
