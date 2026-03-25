#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
cd "$REPO_ROOT"
exec "$PYTHON_BIN" manage.py runserver "$@"
