#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

sh "$SCRIPT_DIR/quality-core.sh"
sh "$SCRIPT_DIR/test-browser.sh"
sh "$SCRIPT_DIR/test-browser-storyboard.sh"
