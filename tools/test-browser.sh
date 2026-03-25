#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/common.sh"

TIMEPOLL_REQUIRE_BROWSER_TESTS=${TIMEPOLL_REQUIRE_BROWSER_TESTS:-1}
export TIMEPOLL_REQUIRE_BROWSER_TESTS

run_manage test --tag=browser "$@"
