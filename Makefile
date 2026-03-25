PYTHON ?= venv/bin/python
PIP ?= venv/bin/pip
PLAYWRIGHT_INSTALL_ARGS ?= chromium
PIP_AUDIT_IGNORE ?= GHSA-5239-wwwm-4pmq

TIMEPOLL_SECRET_KEY ?= dev-only-secret-change-me
TIMEPOLL_DEBUG ?= 1
TIMEPOLL_ALLOWED_HOSTS ?= 127.0.0.1,localhost,testserver,[::1]

DJANGO_ENV = TIMEPOLL_SECRET_KEY="$(TIMEPOLL_SECRET_KEY)" TIMEPOLL_DEBUG="$(TIMEPOLL_DEBUG)" TIMEPOLL_ALLOWED_HOSTS="$(TIMEPOLL_ALLOWED_HOSTS)"

.PHONY: install-dev install-browser lint typecheck security audit test coverage quality

install-dev:
	$(PIP) install -r requirements-dev.txt

install-browser:
	$(PYTHON) -m playwright install $(PLAYWRIGHT_INSTALL_ARGS)

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy polls timepoll manage.py

security:
	$(PYTHON) -m bandit --ini .bandit -r polls timepoll manage.py

audit:
	$(PYTHON) -m pip_audit -r requirements-dev.txt --ignore-vuln $(PIP_AUDIT_IGNORE)

test:
	$(DJANGO_ENV) $(PYTHON) manage.py test

coverage:
	$(DJANGO_ENV) $(PYTHON) -m coverage run manage.py test
	$(PYTHON) -m coverage report --show-missing
	$(PYTHON) -m coverage xml

quality: lint typecheck security audit coverage
