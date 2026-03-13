# TimePoll

Django + Vue.js polling app for scheduling meetings with multilingual UI (`en`, `fi`, `sv`, `no`, `et`).

## Requirements

- Python 3.9+

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
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

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

```bash
python manage.py test
```

## CI merge gates

This repository includes GitHub Actions checks in `.github/workflows/ci.yml`:

- `ruff check .`
- `mypy polls timepoll manage.py --ignore-missing-imports --exclude "polls/migrations/.*"`
- `bandit -r polls timepoll manage.py -x polls/migrations`
- `pip-audit --requirement requirements.txt`
- `python manage.py test`

To enforce these checks as merge gates in GitHub:

1. Enable branch protection on your default branch.
2. Enable `Require a pull request before merging`.
3. Enable `Require review from Code Owners`.
4. Enable `Require status checks to pass before merging` and select `CI / quality`.

## Notes

- Vue app code is in Django static files.
- Vue runtime is loaded from Wikimedia CDN: `https://tools-static.wmflabs.org/cdnjs/...`.
- Required environment variables:
  - `TIMEPOLL_SECRET_KEY`: non-empty secret string
  - `TIMEPOLL_DEBUG`: boolean-like string (`1/0`, `true/false`, `yes/no`, `on/off`)
  - `TIMEPOLL_ALLOWED_HOSTS`: comma-separated hostnames (for example `127.0.0.1,localhost`)
