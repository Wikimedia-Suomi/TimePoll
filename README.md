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

## Local development (virtualenv)

1. Create and activate virtualenv:

```bash
python3.13 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional development tooling:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
```

This also installs `pytest`, `pytest-django`, and `hypothesis`.

3. Set required environment variables:

```bash
export TIMEPOLL_SECRET_KEY='dev-only-secret-change-me'
export TIMEPOLL_DEBUG='1'
export TIMEPOLL_ALLOWED_HOSTS='127.0.0.1,localhost'
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Start development server:

```bash
python manage.py runserver
```

6. Open app:

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Optional poll link format with custom identifier:

- `http://127.0.0.1:8000/?id=Poll_Name_2026`

## Tests

Run the backend Django suite:

```bash
python manage.py test --exclude-tag=browser
# or
make test
```

Run the tagged Playwright browser suite explicitly:

```bash
python manage.py test --tag=browser
# or
make test-browser
```

Run the core automated quality checks:

```bash
make quality
```

Run the full quality suite, including Playwright browser tests:

```bash
make quality-full
```

Run the Django suite with `pytest`:

```bash
make pytest
```

Available local automation targets:

- `make install-dev`
- `make install-browser`
- `make lint`
- `make typecheck`
- `make security`
- `make audit`
- `make test`
- `make test-browser`
- `make pytest`
- `make coverage`
- `make quality`
- `make quality-full`

## CI merge gates

This repository includes GitHub Actions checks in `.github/workflows/ci.yml`:

- `ruff check .`
- `mypy polls timepoll manage.py`
- `bandit -r polls timepoll manage.py`
- `pip-audit --requirement requirements-dev.txt`
- `coverage run manage.py test`
- Playwright browser smoke test
- axe accessibility smoke test

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
- Vue runtime is loaded from Wikimedia CDN: `https://tools-static.wmflabs.org/cdnjs/...`.
- Required environment variables:
  - `TIMEPOLL_SECRET_KEY`: non-empty secret string
  - `TIMEPOLL_DEBUG`: boolean-like string (`1/0`, `true/false`, `yes/no`, `on/off`)
  - `TIMEPOLL_ALLOWED_HOSTS`: comma-separated hostnames (for example `127.0.0.1,localhost`)
