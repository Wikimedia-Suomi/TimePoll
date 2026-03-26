from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
import threading
from contextlib import contextmanager
from ipaddress import ip_address
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

import timepoll.runtime_guard as runtime_guard
from timepoll.runtime_guard import (
    AllowRule,
    FileAccessBlocked,
    OutboundConnectionBlocked,
    PathAllowRule,
    ProcessExecutionBlocked,
    RuntimeAuditGuard,
    RuntimeAuditGuardConfig,
    SQLiteAllowRule,
    SQLiteConnectionBlocked,
    install_runtime_audit_guard,
)


_AUDIT_EVENT_SINKS: list[list[tuple[str, tuple[object, ...]]]] = []


def _capture_runtime_audit_event(event: str, args: tuple[object, ...]) -> None:
    if event not in {
        "socket.getaddrinfo",
        "socket.connect",
        "open",
        "sqlite3.connect",
        "subprocess.Popen",
    }:
        return
    for sink in list(_AUDIT_EVENT_SINKS):
        sink.append((event, args))


sys.addaudithook(_capture_runtime_audit_event)


@contextmanager
def capture_runtime_audit_events() -> list[tuple[str, tuple[object, ...]]]:
    sink: list[tuple[str, tuple[object, ...]]] = []
    _AUDIT_EVENT_SINKS.append(sink)
    try:
        yield sink
    finally:
        _AUDIT_EVENT_SINKS.remove(sink)


def make_config(
    *,
    network_mode: str = "off",
    allow_rules: tuple[AllowRule, ...] = (),
    process_mode: str = "off",
    file_mode: str = "off",
    read_path_allow_rules: tuple[PathAllowRule, ...] = (),
    write_path_allow_rules: tuple[PathAllowRule, ...] = (),
    sqlite_mode: str = "off",
    sqlite_path_allow_rules: tuple[SQLiteAllowRule, ...] = (),
) -> RuntimeAuditGuardConfig:
    return RuntimeAuditGuardConfig(
        network_mode=network_mode,
        allow_rules=allow_rules,
        process_mode=process_mode,
        file_mode=file_mode,
        read_path_allow_rules=read_path_allow_rules,
        write_path_allow_rules=write_path_allow_rules,
        sqlite_mode=sqlite_mode,
        sqlite_path_allow_rules=sqlite_path_allow_rules,
    )


class RuntimeAuditGuardTests(SimpleTestCase):
    def test_exact_host_and_port_rule_matches(self) -> None:
        rule = AllowRule.parse("api.wikimedia.org:443")

        self.assertTrue(rule.matches("api.wikimedia.org", 443))
        self.assertFalse(rule.matches("api.wikimedia.org", 80))
        self.assertFalse(rule.matches("example.org", 443))

    def test_wildcard_rule_matches_subdomains_only(self) -> None:
        rule = AllowRule.parse("*.wmflabs.org")

        self.assertTrue(rule.matches("tools-static.wmflabs.org", None))
        self.assertFalse(rule.matches("wmflabs.org", None))

    def test_path_rule_matches_nested_paths(self) -> None:
        rule = PathAllowRule.parse("./polls")

        self.assertTrue(rule.matches(Path("polls/tests.py")))
        self.assertFalse(rule.matches(Path("timepoll/settings.py")))

    def test_enforce_mode_blocks_disallowed_connect(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("api.wikimedia.org:443"),),
            )
        )

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(OutboundConnectionBlocked):
                guard.handle_event("socket.connect", (object(), ("example.com", 443)))

    def test_explicit_loopback_rule_allows_only_matching_port(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("localhost:8000"),),
            )
        )

        guard.handle_event("socket.connect", (object(), ("localhost", 8000)))

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(OutboundConnectionBlocked):
                guard.handle_event("socket.connect", (object(), ("127.0.0.1", 9999)))

    def test_log_mode_warns_without_raising(self) -> None:
        guard = RuntimeAuditGuard(make_config(network_mode="log"))

        with patch("timepoll.runtime_guard._emit_warning") as emit_warning:
            guard.handle_event("socket.connect", (object(), ("example.com", 443)))

        emit_warning.assert_called_once()

    def test_allowed_hostname_connects_after_resolved_endpoint_is_recorded(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("api.wikimedia.org:443"),),
            )
        )

        guard.remember_allowed_resolution(
            "api.wikimedia.org",
            443,
            [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443)),
                (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::10", 443, 0, 0)),
            ],
        )

        guard.handle_event("socket.connect", (object(), ("203.0.113.10", 443)))
        guard.handle_event("socket.connect", (object(), ("2001:db8::10", 443, 0, 0)))

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(OutboundConnectionBlocked):
                guard.handle_event("socket.connect", (object(), ("203.0.113.10", 80)))

    def test_resolved_endpoint_is_not_retained_as_stable_ip_allowlist(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("api.wikimedia.org:443"),),
            )
        )

        guard.remember_allowed_resolution(
            "api.wikimedia.org",
            443,
            [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443)),
            ],
        )

        guard.handle_event("socket.connect", (object(), ("203.0.113.10", 443)))

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(OutboundConnectionBlocked):
                guard.handle_event("socket.connect", (object(), ("203.0.113.10", 443)))

    def test_pending_resolution_does_not_cross_threads(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("api.wikimedia.org:443"),),
            )
        )

        def remember_resolution() -> None:
            guard.remember_allowed_resolution(
                "api.wikimedia.org",
                443,
                [
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443)),
                ],
            )

        worker = threading.Thread(target=remember_resolution)
        worker.start()
        worker.join()

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(OutboundConnectionBlocked):
                guard.handle_event("socket.connect", (object(), ("203.0.113.10", 443)))

    def test_service_name_port_matches_host_rule(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                network_mode="enforce",
                allow_rules=(AllowRule.parse("api.wikimedia.org:443"),),
            )
        )

        guard.handle_event(
            "socket.getaddrinfo",
            ("api.wikimedia.org", "https", 0, socket.SOCK_STREAM, socket.IPPROTO_TCP),
        )

    def test_enforce_mode_blocks_unlisted_process_execution(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                process_mode="enforce",
            )
        )

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(ProcessExecutionBlocked):
                guard.handle_event(
                    "subprocess.Popen",
                    ("/bin/bash", ["/bin/bash", "-lc", "echo nope"], None, None),
                )

    def test_enforce_mode_blocks_unlisted_file_read(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                file_mode="enforce",
                read_path_allow_rules=(PathAllowRule.parse("./polls"),),
            )
        )

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(FileAccessBlocked):
                guard.handle_event(
                    "open",
                    ("timepoll/settings.py", "r", 0),
                )

    def test_file_guard_allows_expected_write_path(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                file_mode="enforce",
                write_path_allow_rules=(PathAllowRule.parse("./tmp"),),
            )
        )

        guard.handle_event(
            "open",
            ("tmp/output.txt", "w", 0),
        )

    def test_actual_file_write_audit_payload_drives_write_guard(self) -> None:
        output_path = Path(os.getenv("TMPDIR") or "/tmp") / "runtime-guard-write-payload.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with capture_runtime_audit_events() as events:
                with open(output_path, "w", encoding="utf-8") as handle:
                    handle.write("payload")

            open_events = [
                args
                for event, args in events
                if event == "open"
                and Path(os.fspath(args[0])) == output_path
            ]
            self.assertTrue(open_events)

            actual_write_event = open_events[-1]
            allow_guard = RuntimeAuditGuard(
                make_config(
                    file_mode="enforce",
                    write_path_allow_rules=(PathAllowRule.parse(str(output_path.parent)),),
                )
            )
            allow_guard.handle_event("open", actual_write_event)

            block_guard = RuntimeAuditGuard(
                make_config(
                    file_mode="enforce",
                    write_path_allow_rules=(PathAllowRule.parse("./polls"),),
                )
            )
            with patch("timepoll.runtime_guard._emit_warning"):
                with self.assertRaises(FileAccessBlocked):
                    block_guard.handle_event("open", actual_write_event)
        finally:
            output_path.unlink(missing_ok=True)

    def test_enforce_mode_blocks_unlisted_sqlite_database(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                sqlite_mode="enforce",
                sqlite_path_allow_rules=(SQLiteAllowRule.parse("./db.sqlite3"),),
            )
        )

        with patch("timepoll.runtime_guard._emit_warning"):
            with self.assertRaises(SQLiteConnectionBlocked):
                guard.handle_event("sqlite3.connect", ("other.sqlite3",))

    def test_sqlite_guard_allows_memory_database_when_listed(self) -> None:
        guard = RuntimeAuditGuard(
            make_config(
                sqlite_mode="enforce",
                sqlite_path_allow_rules=(SQLiteAllowRule.parse(":memory:"),),
            )
        )

        guard.handle_event("sqlite3.connect", (":memory:",))

    def test_sqlite_memory_uri_prefix_requires_mode_memory(self) -> None:
        rule = SQLiteAllowRule.parse("sqlite-memory-prefix:memorydb_")

        self.assertTrue(rule.matches("file:memorydb_default?mode=memory&cache=shared"))
        self.assertFalse(rule.matches("file:memorydb_default"))
        self.assertFalse(rule.matches("file:memorydb_default?mode=ro"))
        self.assertFalse(rule.matches("file:memorydb_default?cache=shared"))

    def test_sqlite_exact_file_uri_matches_itself(self) -> None:
        rule = SQLiteAllowRule.parse("file:db.sqlite3")

        self.assertTrue(rule.matches("file:db.sqlite3"))
        self.assertFalse(rule.matches("file:db.sqlite3?mode=memory&cache=shared"))

    def test_sqlite_exact_file_uri_with_trailing_underscore_matches_itself(self) -> None:
        rule = SQLiteAllowRule.parse("file:backup_")

        self.assertTrue(rule.matches("file:backup_"))
        self.assertFalse(rule.matches("file:backup_?mode=memory&cache=shared"))

    def test_actual_socket_audit_payload_uses_numeric_connect_destination(self) -> None:
        if self._effective_guard_mode("TIMEPOLL_AUDIT_NETWORK_MODE") != "off":
            self.skipTest("Network guard blocks real socket payload capture in guard profiles.")

        with capture_runtime_audit_events() as events:
            try:
                socket.create_connection(("localhost", 9), timeout=0.01)
            except OSError:
                pass

        connect_hosts = [
            str(args[1][0])
            for event, args in events
            if event == "socket.connect"
            and len(args) > 1
            and isinstance(args[1], tuple)
            and args[1]
        ]

        self.assertTrue(connect_hosts)
        self.assertTrue(any(host != "localhost" for host in connect_hosts))
        self.assertTrue(any(self._is_ip_address(host) for host in connect_hosts))

    def test_actual_sqlite_audit_payload_keeps_full_uri(self) -> None:
        uri = "file:memorydb_default?mode=memory&cache=shared"

        with capture_runtime_audit_events() as events:
            connection = sqlite3.connect(uri, uri=True)
            connection.close()

        self.assertIn(
            ("sqlite3.connect", (uri,)),
            events,
        )

    def test_actual_file_audit_payload_matches_open_shape(self) -> None:
        with capture_runtime_audit_events() as events:
            with open("README.md", encoding="utf-8") as handle:
                handle.read(1)

        open_events = [args for event, args in events if event == "open"]
        self.assertTrue(open_events)
        self.assertTrue(any(args[0] == "README.md" for args in open_events))
        self.assertTrue(any(isinstance(args[1], str) for args in open_events))
        self.assertTrue(any(isinstance(args[2], int) for args in open_events))

    def test_actual_subprocess_audit_payload_matches_popen_shape(self) -> None:
        if self._effective_guard_mode("TIMEPOLL_AUDIT_PROCESS_MODE") != "off":
            self.skipTest("Process guard blocks real subprocess payload capture in guard profiles.")

        with capture_runtime_audit_events() as events:
            completed = subprocess.run(
                [sys.executable, "-c", "pass"],
                check=False,
            )

        self.assertEqual(completed.returncode, 0)
        popen_events = [args for event, args in events if event == "subprocess.Popen"]
        self.assertTrue(popen_events)
        self.assertTrue(any(args[0] == sys.executable for args in popen_events))
        self.assertTrue(
            any(
                isinstance(args[1], list)
                and args[1]
                and args[1][0] == sys.executable
                for args in popen_events
            )
        )

    @staticmethod
    def _is_ip_address(value: str) -> bool:
        try:
            ip_address(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _effective_guard_mode(name: str) -> str:
        return os.getenv(name) or os.getenv("TIMEPOLL_AUDIT_GUARD_MODE") or "off"

    @patch("timepoll.runtime_guard._install_guarded_socket_getaddrinfo")
    @patch("timepoll.runtime_guard.sys.addaudithook")
    @patch("timepoll.runtime_guard.os.getenv")
    def test_install_reads_environment_and_registers_hook_once(
        self,
        getenv_mock,
        addaudithook_mock,
        install_network_wrapper_mock,
    ) -> None:
        values = {
            "TIMEPOLL_AUDIT_GUARD_MODE": "off",
            "TIMEPOLL_AUDIT_NETWORK_MODE": "enforce",
            "TIMEPOLL_AUDIT_PROCESS_MODE": "log",
            "TIMEPOLL_AUDIT_FILE_MODE": "log",
            "TIMEPOLL_AUDIT_SQLITE_MODE": "enforce",
            "TIMEPOLL_AUDIT_ALLOWLIST": "localhost:8000,[::1]:8000",
            "TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST": "./polls,./timepoll",
            "TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST": "./tmp,./db.sqlite3",
            "TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST": "./db.sqlite3,:memory:",
        }
        getenv_mock.side_effect = lambda name, default=None: values.get(name, default)

        with patch("timepoll.runtime_guard._AUDIT_GUARD_INSTALLED", False):
            config = install_runtime_audit_guard()

        self.assertEqual(config.network_mode, "enforce")
        self.assertEqual(config.process_mode, "log")
        self.assertEqual(config.file_mode, "log")
        self.assertEqual(config.sqlite_mode, "enforce")
        self.assertEqual(addaudithook_mock.call_count, 1)
        install_network_wrapper_mock.assert_called_once()

    @patch("timepoll.runtime_guard.sys.addaudithook")
    @patch("timepoll.runtime_guard.os.getenv")
    def test_install_wrapper_allows_resolved_loopback_endpoint_end_to_end(
        self,
        getenv_mock,
        addaudithook_mock,
    ) -> None:
        values = {
            "TIMEPOLL_AUDIT_GUARD_MODE": "off",
            "TIMEPOLL_AUDIT_NETWORK_MODE": "enforce",
            "TIMEPOLL_AUDIT_PROCESS_MODE": "off",
            "TIMEPOLL_AUDIT_FILE_MODE": "off",
            "TIMEPOLL_AUDIT_SQLITE_MODE": "off",
            "TIMEPOLL_AUDIT_ALLOWLIST": "localhost:8000",
        }
        fake_results = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 8000)),
        ]
        getenv_mock.side_effect = lambda name, default=None: values.get(name, default)

        with (
            patch.object(socket, "getaddrinfo", socket.getaddrinfo),
            patch("timepoll.runtime_guard._ORIGINAL_SOCKET_GETADDRINFO", return_value=fake_results) as original_getaddrinfo_mock,
            patch("timepoll.runtime_guard._AUDIT_GUARD_INSTALLED", False),
            patch("timepoll.runtime_guard._ACTIVE_NETWORK_GUARD", None),
            patch("timepoll.runtime_guard._SOCKET_GETADDRINFO_PATCHED", False),
        ):
            install_runtime_audit_guard()
            self.assertIs(socket.getaddrinfo, runtime_guard._guarded_socket_getaddrinfo)

            resolved = runtime_guard._guarded_socket_getaddrinfo(
                "localhost",
                8000,
                0,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
            )
            self.assertEqual(fake_results, resolved)
            original_getaddrinfo_mock.assert_called_once()

            installed_hook = addaudithook_mock.call_args.args[0]
            installed_hook("socket.connect", (object(), ("127.0.0.1", 8000)))

            with patch("timepoll.runtime_guard._emit_warning"):
                with self.assertRaises(OutboundConnectionBlocked):
                    installed_hook("socket.connect", (object(), ("127.0.0.1", 9999)))

    @patch("timepoll.runtime_guard.os.getenv")
    def test_install_rejects_external_network_allowlists_in_enforce_mode(
        self,
        getenv_mock,
    ) -> None:
        values = {
            "TIMEPOLL_AUDIT_GUARD_MODE": "off",
            "TIMEPOLL_AUDIT_NETWORK_MODE": "enforce",
            "TIMEPOLL_AUDIT_PROCESS_MODE": "off",
            "TIMEPOLL_AUDIT_FILE_MODE": "off",
            "TIMEPOLL_AUDIT_SQLITE_MODE": "off",
            "TIMEPOLL_AUDIT_ALLOWLIST": "api.wikimedia.org:443",
        }
        getenv_mock.side_effect = lambda name, default=None: values.get(name, default)

        with patch("timepoll.runtime_guard._AUDIT_GUARD_INSTALLED", False):
            with self.assertRaisesRegex(ValueError, "does not support external host allowlist rules"):
                install_runtime_audit_guard()
