#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
run_in_repo "$PYTHON_BIN" -m coverage run manage.py test --exclude-tag=browser "$@"
run_in_repo "$PYTHON_BIN" -m coverage report --show-missing
run_in_repo "$PYTHON_BIN" -m coverage xml
