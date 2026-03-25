#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

ensure_venv
run_in_repo "$PYTHON_BIN" -m pip install --upgrade pip
run_in_repo "$PYTHON_BIN" -m pip install -r requirements-dev.txt
