# TimePoll2

Django + Vue.js polling app (Doodle-style) with multilingual UI (`en`, `fi`, `sv`, `no`, `et`).

## Requirements

- Python 3.9+

## Features

- Vue.js frontend with static assets under `polls/static/`
- JSON API backend in Django for fast interactions (no full-page reload required)
- Poll lifecycle:
  - Create poll from full start/end days (slots are always 60 minutes) (requires login)
  - Limit poll slots by daily start/end hour, selected weekdays, and poll timezone
  - Automatic slot grid generation
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

3. Load local development environment variables:

```bash
source ./local-dev-env.sh
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

## Tests

```bash
source ./local-dev-env.sh
python manage.py test
```

## Notes

- Vue app code is in Django static files.
- Vue runtime is loaded from Wikimedia CDN: `https://tools-static.wmflabs.org/cdnjs/...`.
- `local-dev-env.sh` creates/loads local env vars needed by settings (`TIMEPOLL_SECRET_KEY`, `TIMEPOLL_DEBUG`, `TIMEPOLL_ALLOWED_HOSTS`).
