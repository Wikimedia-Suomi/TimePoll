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

## Commands

Canonical project commands live in `tools/`. `Makefile` is optional and only provides shortcuts for them.

Core workflow:

```bash
sh tools/dev.sh
sh tools/test-backend.sh
sh tools/quality-core.sh
```

Browser and full quality workflow:

```bash
sh tools/install-browser.sh
sh tools/test-browser.sh
sh tools/quality-full.sh
```

Optional `make` shortcuts:

```bash
make dev
make test
make quality
make test-browser
make quality-full
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
sh tools/quality-core.sh
```

Browser and full quality:

```bash
sh tools/install-browser.sh
sh tools/test-browser.sh
sh tools/quality-full.sh
```

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

Note: the `pip-audit` target currently ignores advisory `GHSA-5239-wwwm-4pmq`
for `pygments`, because no fixed upstream release is available yet.

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
