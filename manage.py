#!/usr/bin/env python3
import os
import sys

from timepoll.runtime_guard import install_runtime_audit_guard


def main() -> None:
    install_runtime_audit_guard()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "timepoll.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available in your virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
