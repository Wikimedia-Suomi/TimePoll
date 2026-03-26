#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

use_backend_test_file_enforce_smoke_profile
run_manage test polls.tests.SecurityHeaderTests polls.test_runtime_guard.RuntimeAuditGuardTests "$@"
