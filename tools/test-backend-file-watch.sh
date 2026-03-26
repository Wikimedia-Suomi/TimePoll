#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

use_backend_test_file_watch_profile
run_manage test --exclude-tag=browser --exclude-tag=browser_storyboard "$@"
