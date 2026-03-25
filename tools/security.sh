#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
run_in_repo "$PYTHON_BIN" -m bandit --ini .bandit -r polls timepoll manage.py "$@"
