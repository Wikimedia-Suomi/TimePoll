#!/bin/sh

TOOLS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$TOOLS_DIR/.." && pwd)

VENV_DIR=${VENV_DIR:-"$REPO_ROOT/venv"}
PYTHON_BIN=${PYTHON_BIN:-"$VENV_DIR/bin/python"}
PIP_BIN=${PIP_BIN:-"$VENV_DIR/bin/pip"}

TIMEPOLL_SECRET_KEY=${TIMEPOLL_SECRET_KEY:-dev-only-secret-change-me}
TIMEPOLL_DEBUG=${TIMEPOLL_DEBUG:-1}
TIMEPOLL_ALLOWED_HOSTS=${TIMEPOLL_ALLOWED_HOSTS:-127.0.0.1,localhost,testserver,[::1]}

PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH:-"$REPO_ROOT/.playwright-browsers"}
PLAYWRIGHT_INSTALL_ARGS=${PLAYWRIGHT_INSTALL_ARGS:-chromium}
PIP_AUDIT_IGNORE=${PIP_AUDIT_IGNORE:-GHSA-5239-wwwm-4pmq}
COVERAGE_FAIL_UNDER=${COVERAGE_FAIL_UNDER:-92}

export REPO_ROOT VENV_DIR PYTHON_BIN PIP_BIN
export TIMEPOLL_SECRET_KEY TIMEPOLL_DEBUG TIMEPOLL_ALLOWED_HOSTS
export PLAYWRIGHT_BROWSERS_PATH PLAYWRIGHT_INSTALL_ARGS PIP_AUDIT_IGNORE COVERAGE_FAIL_UNDER

build_python_runtime_read_allowlist() {
    require_venv
    run_in_repo "$PYTHON_BIN" - <<'PY'
import site
import sys
import sysconfig
from pathlib import Path

items = []
for key in ("stdlib", "platstdlib", "purelib", "platlib", "data"):
    value = sysconfig.get_paths().get(key)
    if value:
        items.append(value)
for value in (sys.prefix, sys.base_prefix):
    if value:
        items.append(value)
for value in site.getsitepackages():
    items.append(value)

normalized = []
seen = set()
for item in items:
    path = str(Path(item).resolve(strict=False))
    if path not in seen:
        seen.add(path)
        normalized.append(path)

print(",".join(normalized))
PY
}

use_backend_test_guard_profile() {
    TIMEPOLL_AUDIT_GUARD_MODE=${TIMEPOLL_AUDIT_GUARD_MODE:-off}
    TIMEPOLL_AUDIT_NETWORK_MODE=${TIMEPOLL_AUDIT_NETWORK_MODE:-enforce}
    TIMEPOLL_AUDIT_PROCESS_MODE=${TIMEPOLL_AUDIT_PROCESS_MODE:-enforce}
    TIMEPOLL_AUDIT_FILE_MODE=${TIMEPOLL_AUDIT_FILE_MODE:-off}
    TIMEPOLL_AUDIT_SQLITE_MODE=${TIMEPOLL_AUDIT_SQLITE_MODE:-enforce}
    TIMEPOLL_AUDIT_ALLOWLIST=${TIMEPOLL_AUDIT_ALLOWLIST:-}
    TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST:-"$REPO_ROOT,$VENV_DIR,${TMPDIR:-/tmp},/tmp"}
    TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST:-"$REPO_ROOT/.coverage,$REPO_ROOT/coverage.xml,$REPO_ROOT/.hypothesis,${TMPDIR:-/tmp},/tmp"}
    TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST:-"$REPO_ROOT/db.sqlite3,:memory:,sqlite-memory-prefix:memorydb_"}

    export TIMEPOLL_AUDIT_GUARD_MODE
    export TIMEPOLL_AUDIT_NETWORK_MODE TIMEPOLL_AUDIT_PROCESS_MODE
    export TIMEPOLL_AUDIT_FILE_MODE TIMEPOLL_AUDIT_SQLITE_MODE
    export TIMEPOLL_AUDIT_ALLOWLIST
    export TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST
    export TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST
}

use_backend_test_file_watch_profile() {
    use_backend_test_guard_profile
    TIMEPOLL_AUDIT_FILE_MODE=${TIMEPOLL_AUDIT_FILE_MODE:-log}
    TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST:-"$REPO_ROOT,$VENV_DIR,${TMPDIR:-/tmp},/tmp"}
    TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST:-"$REPO_ROOT/db.sqlite3,$REPO_ROOT/.coverage,$REPO_ROOT/coverage.xml,$REPO_ROOT/.hypothesis,${TMPDIR:-/tmp},/tmp"}

    export TIMEPOLL_AUDIT_FILE_MODE
    export TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST
}

use_backend_test_file_enforce_smoke_profile() {
    use_backend_test_guard_profile
    PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE:-1}
    python_runtime_roots=$(build_python_runtime_read_allowlist)

    TIMEPOLL_AUDIT_NETWORK_MODE=${TIMEPOLL_AUDIT_NETWORK_MODE:-enforce}
    TIMEPOLL_AUDIT_PROCESS_MODE=${TIMEPOLL_AUDIT_PROCESS_MODE:-enforce}
    TIMEPOLL_AUDIT_FILE_MODE=${TIMEPOLL_AUDIT_FILE_MODE:-enforce}
    TIMEPOLL_AUDIT_SQLITE_MODE=${TIMEPOLL_AUDIT_SQLITE_MODE:-enforce}
    TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST:-"$REPO_ROOT,$VENV_DIR,$python_runtime_roots,${TMPDIR:-/tmp},/tmp"}
    TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST:-"${TMPDIR:-/tmp},/tmp"}
    TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST=${TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST:-":memory:,sqlite-memory-prefix:memorydb_"}

    export PYTHONDONTWRITEBYTECODE
    export TIMEPOLL_AUDIT_NETWORK_MODE TIMEPOLL_AUDIT_PROCESS_MODE
    export TIMEPOLL_AUDIT_FILE_MODE TIMEPOLL_AUDIT_SQLITE_MODE
    export TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST
    export TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST
}

find_bootstrap_python() {
    if [ -n "${BOOTSTRAP_PYTHON:-}" ]; then
        if command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
            printf '%s\n' "$BOOTSTRAP_PYTHON"
            return 0
        fi
        echo "BOOTSTRAP_PYTHON '$BOOTSTRAP_PYTHON' was not found in PATH." >&2
        return 1
    fi

    for candidate in python3.13 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    echo "Python 3.13+ is required. Set BOOTSTRAP_PYTHON if your interpreter has a different name." >&2
    return 1
}

ensure_venv() {
    if [ -x "$PYTHON_BIN" ] && [ -x "$PIP_BIN" ]; then
        return 0
    fi

    bootstrap_python=$(find_bootstrap_python)
    mkdir -p "$(dirname -- "$VENV_DIR")"
    "$bootstrap_python" -m venv "$VENV_DIR"
}

require_venv() {
    if [ ! -x "$PYTHON_BIN" ]; then
        echo "Missing virtualenv at '$VENV_DIR'. Run 'sh tools/install-dev.sh' first." >&2
        exit 1
    fi
}

run_in_repo() {
    (
        cd "$REPO_ROOT"
        "$@"
    )
}

run_manage() {
    require_venv
    run_in_repo "$PYTHON_BIN" manage.py "$@"
}
