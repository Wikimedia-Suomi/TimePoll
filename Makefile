PYTHON ?= venv/bin/python
PIP ?= venv/bin/pip
PLAYWRIGHT_INSTALL_ARGS ?= chromium
PIP_AUDIT_IGNORE ?= GHSA-5239-wwwm-4pmq
COVERAGE_FAIL_UNDER ?= 92

TIMEPOLL_SECRET_KEY ?= dev-only-secret-change-me
TIMEPOLL_DEBUG ?= 1
TIMEPOLL_ALLOWED_HOSTS ?= 127.0.0.1,localhost,testserver,[::1]
PLAYWRIGHT_BROWSERS_PATH ?= $(CURDIR)/.playwright-browsers

TOOL_ENV = PYTHON_BIN="$(PYTHON)" PIP_BIN="$(PIP)" PLAYWRIGHT_INSTALL_ARGS="$(PLAYWRIGHT_INSTALL_ARGS)" PIP_AUDIT_IGNORE="$(PIP_AUDIT_IGNORE)" PLAYWRIGHT_BROWSERS_PATH="$(PLAYWRIGHT_BROWSERS_PATH)" COVERAGE_FAIL_UNDER="$(COVERAGE_FAIL_UNDER)" TIMEPOLL_SECRET_KEY="$(TIMEPOLL_SECRET_KEY)" TIMEPOLL_DEBUG="$(TIMEPOLL_DEBUG)" TIMEPOLL_ALLOWED_HOSTS="$(TIMEPOLL_ALLOWED_HOSTS)"

.PHONY: bootstrap dev install-dev install-browser lint typecheck security audit test test-browser test-browser-storyboard pytest coverage quality quality-full

bootstrap:
	$(TOOL_ENV) sh tools/bootstrap.sh

dev:
	$(TOOL_ENV) sh tools/dev.sh

install-dev:
	$(TOOL_ENV) sh tools/install-dev.sh

install-browser:
	$(TOOL_ENV) sh tools/install-browser.sh

lint:
	$(TOOL_ENV) sh tools/lint.sh

typecheck:
	$(TOOL_ENV) sh tools/typecheck.sh

security:
	$(TOOL_ENV) sh tools/security.sh

audit:
	$(TOOL_ENV) sh tools/audit.sh

test:
	$(TOOL_ENV) sh tools/test-backend.sh

test-browser:
	$(TOOL_ENV) sh tools/test-browser.sh

test-browser-storyboard:
	$(TOOL_ENV) sh tools/test-browser-storyboard.sh

pytest:
	$(TOOL_ENV) sh tools/pytest.sh

coverage:
	$(TOOL_ENV) sh tools/coverage.sh

quality:
	$(TOOL_ENV) sh tools/quality-core.sh

quality-full:
	$(TOOL_ENV) sh tools/quality-full.sh
