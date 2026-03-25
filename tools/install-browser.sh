#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

set -- $PLAYWRIGHT_INSTALL_ARGS "$@"
run_in_repo "$PYTHON_BIN" -m playwright install "$@"
