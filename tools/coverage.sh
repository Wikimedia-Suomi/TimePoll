#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
run_in_repo "$PYTHON_BIN" -m coverage run manage.py test --exclude-tag=browser --exclude-tag=browser_storyboard "$@"
run_in_repo "$PYTHON_BIN" -m coverage report --show-missing --fail-under="$COVERAGE_FAIL_UNDER"
run_in_repo "$PYTHON_BIN" -m coverage xml
