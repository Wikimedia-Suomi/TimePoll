#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

sh "$SCRIPT_DIR/lint.sh"
sh "$SCRIPT_DIR/typecheck.sh"
sh "$SCRIPT_DIR/security.sh"
sh "$SCRIPT_DIR/audit.sh"
sh "$SCRIPT_DIR/coverage.sh"
