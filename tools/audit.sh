#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

require_venv
run_in_repo "$PIP_AUDIT_BIN" --cache-dir "$PIP_AUDIT_CACHE_DIR" -r requirements-dev.txt --ignore-vuln "$PIP_AUDIT_IGNORE" "$@"
