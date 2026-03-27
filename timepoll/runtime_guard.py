from __future__ import annotations

import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

VALID_GUARD_MODES = {"off", "log", "enforce"}


def _parse_guard_mode(name: str, *, default: str) -> str:
    raw = os.getenv(name, default)
    normalized = raw.strip().lower()
    if normalized not in VALID_GUARD_MODES:
        raise ValueError(f"{name} must be one of: off, log, enforce.")
    return normalized


def _normalize_host(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return ""
    if trimmed.startswith("[") and trimmed.endswith("]"):
        return trimmed[1:-1].lower()
    return trimmed.lower()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_path(value: Any) -> Path | None:
    raw = _normalize_text(value)
    if raw is None or not raw or raw.startswith("<"):
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


@dataclass(frozen=True)
class AllowRule:
    host_pattern: str
    port: int | None = None

    @classmethod
    def parse(cls, raw_value: str) -> "AllowRule":
        value = raw_value.strip()
        if not value:
            raise ValueError("Allow rule cannot be empty.")
        if value.startswith("["):
            end = value.find("]")
            if end == -1:
                raise ValueError(f"Invalid IPv6 allow rule: {raw_value}")
            host = _normalize_host(value[: end + 1])
            remainder = value[end + 1 :]
            if remainder.startswith(":") and remainder[1:].isdigit():
                return cls(host_pattern=host, port=int(remainder[1:]))
            if remainder:
                raise ValueError(f"Invalid IPv6 allow rule: {raw_value}")
            return cls(host_pattern=host)

        host, separator, port_text = value.rpartition(":")
        if separator and host and port_text.isdigit() and ":" not in host:
            return cls(host_pattern=_normalize_host(host), port=int(port_text))
        return cls(host_pattern=_normalize_host(value))

    def matches(self, host: str, port: int | None) -> bool:
        normalized_host = _normalize_host(host)
        if not normalized_host:
            return False
        if self.port is not None and self.port != port:
            return False
        if self.host_pattern.startswith("*."):
            suffix = self.host_pattern[1:]
            return normalized_host.endswith(suffix) and normalized_host != suffix[1:]
        return normalized_host == self.host_pattern


@dataclass(frozen=True)
class PathAllowRule:
    raw_pattern: str
    normalized_path: Path | None = None
    literal_prefix: str | None = None

    @classmethod
    def parse(cls, raw_value: str) -> "PathAllowRule":
        value = raw_value.strip()
        if not value:
            raise ValueError("Path allow rule cannot be empty.")
        if value == ":memory:" or value.startswith("file:"):
            return cls(raw_pattern=value, literal_prefix=value)
        normalized_path = _normalize_path(value)
        if normalized_path is None:
            raise ValueError(f"Invalid path allow rule: {raw_value}")
        return cls(raw_pattern=value, normalized_path=normalized_path)

    def matches(self, value: Any) -> bool:
        if self.literal_prefix is not None:
            candidate = _normalize_text(value)
            if candidate is None:
                return False
            return candidate == self.literal_prefix or candidate.startswith(self.literal_prefix)

        candidate_path = _normalize_path(value)
        if candidate_path is None or self.normalized_path is None:
            return False
        return candidate_path == self.normalized_path or self.normalized_path in candidate_path.parents


def _coerce_port(
    value: Any,
    *,
    socktype: int | None = None,
    protocol: int | None = None,
) -> int | None:
    if isinstance(value, int):
        return value

    text = _normalize_text(value)
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.isdigit():
        return int(stripped)

    protocol_candidates: list[str | None] = []
    if protocol == getattr(socket, "IPPROTO_TCP", None) or socktype == getattr(socket, "SOCK_STREAM", None):
        protocol_candidates.append("tcp")
    elif protocol == getattr(socket, "IPPROTO_UDP", None) or socktype == getattr(socket, "SOCK_DGRAM", None):
        protocol_candidates.append("udp")
    protocol_candidates.extend([None, "tcp", "udp"])

    seen: set[str | None] = set()
    for protocol_name in protocol_candidates:
        if protocol_name in seen:
            continue
        seen.add(protocol_name)
        try:
            if protocol_name is None:
                return socket.getservbyname(stripped)
            return socket.getservbyname(stripped, protocol_name)
        except OSError:
            continue
    return None


def _parse_sqlite_uri(value: Any) -> Any | None:
    candidate = _normalize_text(value)
    if candidate is None or not candidate.startswith("file:"):
        return None
    parsed = urlsplit(candidate)
    if parsed.scheme != "file":
        return None
    return parsed


def _sqlite_uses_memory_mode(parsed_uri: Any) -> bool:
    mode_values = parse_qs(parsed_uri.query, keep_blank_values=True).get("mode", [])
    return any(value == "memory" for value in mode_values)


def _is_named_sqlite_memory_uri(parsed_uri: Any) -> bool:
    return bool(parsed_uri.path) and "/" not in parsed_uri.path and "\\" not in parsed_uri.path


SQLITE_MEMORY_PREFIX_SCHEME = "sqlite-memory-prefix:"


@dataclass(frozen=True)
class SQLiteAllowRule:
    raw_pattern: str
    path_rule: PathAllowRule | None = None
    exact_literal: str | None = None
    memory_uri_name_prefix: str | None = None

    @classmethod
    def parse(cls, raw_value: str) -> "SQLiteAllowRule":
        value = raw_value.strip()
        if not value:
            raise ValueError("SQLite allow rule cannot be empty.")
        if value == ":memory:":
            return cls(raw_pattern=value, exact_literal=value)
        if value.startswith(SQLITE_MEMORY_PREFIX_SCHEME):
            prefix = value[len(SQLITE_MEMORY_PREFIX_SCHEME) :].strip()
            if not prefix:
                raise ValueError("SQLite memory prefix rule cannot be empty.")
            return cls(raw_pattern=value, memory_uri_name_prefix=prefix)

        parsed_uri = _parse_sqlite_uri(value)
        if parsed_uri is not None:
            return cls(raw_pattern=value, exact_literal=value)

        return cls(raw_pattern=value, path_rule=PathAllowRule.parse(value))

    def matches(self, value: Any) -> bool:
        if self.path_rule is not None:
            return self.path_rule.matches(value)

        candidate = _normalize_text(value)
        if candidate is None or not candidate:
            return False
        if self.exact_literal is not None:
            return candidate == self.exact_literal
        if self.memory_uri_name_prefix is None:
            return False

        parsed_uri = _parse_sqlite_uri(candidate)
        if parsed_uri is None:
            return False
        if not _is_named_sqlite_memory_uri(parsed_uri):
            return False
        if not _sqlite_uses_memory_mode(parsed_uri):
            return False
        return parsed_uri.path.startswith(self.memory_uri_name_prefix)


@dataclass(frozen=True)
class RuntimeAuditGuardConfig:
    network_mode: str
    allow_rules: tuple[AllowRule, ...]
    process_mode: str
    file_mode: str
    read_path_allow_rules: tuple[PathAllowRule, ...]
    write_path_allow_rules: tuple[PathAllowRule, ...]
    sqlite_mode: str
    sqlite_path_allow_rules: tuple[SQLiteAllowRule, ...]

    @property
    def enabled(self) -> bool:
        return any(
            mode in {"log", "enforce"}
            for mode in (
                self.network_mode,
                self.process_mode,
                self.file_mode,
                self.sqlite_mode,
            )
        )

    def validate_for_startup(self) -> None:
        if self.network_mode != "enforce":
            return
        external_rules = [
            rule
            for rule in self.allow_rules
            if _is_external_allow_rule(rule)
        ]
        if not external_rules:
            return
        formatted_rules = ", ".join(
            rule.host_pattern if rule.port is None else f"{rule.host_pattern}:{rule.port}"
            for rule in external_rules
        )
        raise ValueError(
            "TIMEPOLL_AUDIT_NETWORK_MODE=enforce does not support external host allowlist rules. "
            f"Found: {formatted_rules}. Use explicit loopback allowlist rules in enforce mode, "
            "or switch the network guard to log/off and rely on infrastructure-level egress controls."
        )

    @classmethod
    def from_env(cls) -> "RuntimeAuditGuardConfig":
        global_mode = _parse_guard_mode("TIMEPOLL_AUDIT_GUARD_MODE", default="off")
        network_mode = _parse_guard_mode("TIMEPOLL_AUDIT_NETWORK_MODE", default=global_mode)
        process_mode = _parse_guard_mode("TIMEPOLL_AUDIT_PROCESS_MODE", default=global_mode)
        file_mode = _parse_guard_mode("TIMEPOLL_AUDIT_FILE_MODE", default=global_mode)
        sqlite_mode = _parse_guard_mode("TIMEPOLL_AUDIT_SQLITE_MODE", default=global_mode)

        allow_rules = tuple(
            AllowRule.parse(item)
            for item in os.getenv("TIMEPOLL_AUDIT_ALLOWLIST", "").split(",")
            if item.strip()
        )
        read_path_allow_rules = tuple(
            PathAllowRule.parse(item)
            for item in os.getenv("TIMEPOLL_AUDIT_READ_PATH_ALLOWLIST", "").split(",")
            if item.strip()
        )
        write_path_allow_rules = tuple(
            PathAllowRule.parse(item)
            for item in os.getenv("TIMEPOLL_AUDIT_WRITE_PATH_ALLOWLIST", "").split(",")
            if item.strip()
        )
        sqlite_path_allow_rules = tuple(
            SQLiteAllowRule.parse(item)
            for item in os.getenv("TIMEPOLL_AUDIT_SQLITE_PATH_ALLOWLIST", "").split(",")
            if item.strip()
        )

        return cls(
            network_mode=network_mode,
            allow_rules=allow_rules,
            process_mode=process_mode,
            file_mode=file_mode,
            read_path_allow_rules=read_path_allow_rules,
            write_path_allow_rules=write_path_allow_rules,
            sqlite_mode=sqlite_mode,
            sqlite_path_allow_rules=sqlite_path_allow_rules,
        )


class OutboundConnectionBlocked(PermissionError):
    pass


class ProcessExecutionBlocked(PermissionError):
    pass


class FileAccessBlocked(PermissionError):
    pass


class SQLiteConnectionBlocked(PermissionError):
    pass


def _emit_warning(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _is_ip_literal(host: str) -> bool:
    try:
        ip_address(_normalize_host(host))
        return True
    except ValueError:
        return False


def _is_loopback_host(host: str) -> bool:
    normalized = _normalize_host(host)
    if normalized == "localhost":
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _is_external_allow_rule(rule: AllowRule) -> bool:
    host = _normalize_host(rule.host_pattern)
    if not host:
        return False
    if host.startswith("*."):
        return True
    return not _is_loopback_host(host)


def _coerce_address(value: Any) -> tuple[str | None, int | None]:
    if value is None:
        return None, None
    if isinstance(value, tuple):
        if not value:
            return None, None
        host = value[0]
        port = value[1] if len(value) > 1 and isinstance(value[1], int) else None
        return _normalize_text(host), port
    host = _normalize_text(value)
    if host is None or host.startswith("/"):
        return None, None
    return host, None


def _resolve_subprocess_candidate(event: str, args: tuple[Any, ...]) -> Any:
    if event == "subprocess.Popen":
        executable = args[0] if len(args) > 0 else None
        popen_args = args[1] if len(args) > 1 else None
        if executable:
            return executable
        if isinstance(popen_args, (list, tuple)) and popen_args:
            return popen_args[0]
        return popen_args
    if len(args) > 0:
        return args[0]
    return None


def _is_write_open(mode: Any, flags: Any) -> bool:
    mode_text = _normalize_text(mode) or ""
    if any(marker in mode_text for marker in ("w", "a", "x", "+")):
        return True
    if not isinstance(flags, int):
        return False
    write_bits = (
        os.O_WRONLY
        | os.O_RDWR
        | getattr(os, "O_APPEND", 0)
        | getattr(os, "O_CREAT", 0)
        | getattr(os, "O_TRUNC", 0)
    )
    return bool(flags & write_bits)


class RuntimeAuditGuard:
    MAX_PENDING_RESOLUTION_BATCHES = 16
    PENDING_RESOLUTION_TTL_SECONDS = 5.0
    NETWORK_EVENTS = {
        "socket.getaddrinfo",
        "socket.connect",
        "socket.connect_ex",
        "socket.sendto",
        "socket.sendmsg",
    }
    PROCESS_EVENTS = {"subprocess.Popen", "os.exec", "os.posix_spawn"}
    FILE_EVENTS = {"open"}
    SQLITE_EVENTS = {"sqlite3.connect"}

    def __init__(self, config: RuntimeAuditGuardConfig):
        self.config = config
        self._pending_resolutions = threading.local()

    def handle_event(self, event: str, args: tuple[Any, ...]) -> None:
        if not self.config.enabled:
            return
        if event in self.NETWORK_EVENTS and self.config.network_mode != "off":
            self._handle_network_event(event, args)
            return
        if event in self.PROCESS_EVENTS and self.config.process_mode != "off":
            self._handle_process_event(event, args)
            return
        if event in self.FILE_EVENTS and self.config.file_mode != "off":
            self._handle_file_event(event, args)
            return
        if event in self.SQLITE_EVENTS and self.config.sqlite_mode != "off":
            self._handle_sqlite_event(event, args)

    def is_allowed(self, host: str, port: int | None) -> bool:
        normalized_host = _normalize_host(host)
        if not normalized_host:
            return True
        if self._is_allowed_by_rules(normalized_host, port):
            return True
        if not _is_ip_literal(normalized_host):
            return False
        return self._consume_allowed_resolved_endpoint(normalized_host, port)

    def remember_allowed_resolution(self, host: Any, port: Any, results: Any) -> None:
        normalized_host = _normalize_text(host)
        requested_port = _coerce_port(port)
        if normalized_host is None or not self._is_allowed_by_rules(normalized_host, requested_port):
            return
        if not isinstance(results, (list, tuple)):
            return

        endpoints: set[tuple[str, int | None]] = set()
        for result in results:
            if not isinstance(result, tuple) or len(result) < 5:
                continue
            resolved_host, resolved_port = _coerce_address(result[4])
            if resolved_host is None:
                continue
            normalized_resolved_host = _normalize_host(resolved_host)
            if not _is_ip_literal(normalized_resolved_host):
                continue
            endpoints.add(
                (
                    normalized_resolved_host,
                    resolved_port if resolved_port is not None else requested_port,
                )
            )

        if not endpoints:
            return

        batches = self._get_pending_resolution_batches()
        self._prune_expired_pending_resolution_batches(batches)
        batches.append(
            {
                "endpoints": endpoints,
                "expires_at": time.monotonic() + self.PENDING_RESOLUTION_TTL_SECONDS,
            }
        )
        while len(batches) > self.MAX_PENDING_RESOLUTION_BATCHES:
            batches.pop(0)

    def _is_allowed_by_rules(self, host: str, port: int | None) -> bool:
        normalized_host = _normalize_host(host)
        if not normalized_host:
            return True
        return any(rule.matches(normalized_host, port) for rule in self.config.allow_rules)

    def _get_pending_resolution_batches(self) -> list[dict[str, Any]]:
        batches = getattr(self._pending_resolutions, "batches", None)
        if batches is None:
            batches = []
            self._pending_resolutions.batches = batches
        return batches

    def _prune_expired_pending_resolution_batches(
        self,
        batches: list[dict[str, Any]],
    ) -> None:
        now = time.monotonic()
        batches[:] = [
            batch
            for batch in batches
            if batch["expires_at"] > now and batch["endpoints"]
        ]

    def _consume_allowed_resolved_endpoint(self, host: str, port: int | None) -> bool:
        batches = self._get_pending_resolution_batches()
        self._prune_expired_pending_resolution_batches(batches)

        endpoint = (_normalize_host(host), port)
        fallback_endpoint = (_normalize_host(host), None)
        for batch in reversed(batches):
            endpoints = batch["endpoints"]
            if endpoint in endpoints:
                endpoints.remove(endpoint)
                self._prune_expired_pending_resolution_batches(batches)
                return True
            if port is not None and fallback_endpoint in endpoints:
                endpoints.remove(fallback_endpoint)
                self._prune_expired_pending_resolution_batches(batches)
                return True
        return False

    def _handle_network_event(self, event: str, args: tuple[Any, ...]) -> None:
        host, port = self._extract_destination(event, args)
        if host is None or self.is_allowed(host, port):
            return
        self._block_or_log(
            mode=self.config.network_mode,
            error_type=OutboundConnectionBlocked,
            message=(
                f"[TimePoll runtime guard] blocked outbound network attempt via {event}: "
                f"{host}:{port if port is not None else '*'}"
            ),
        )

    def _handle_process_event(self, event: str, args: tuple[Any, ...]) -> None:
        executable = _resolve_subprocess_candidate(event, args)
        if executable is None:
            return
        self._block_or_log(
            mode=self.config.process_mode,
            error_type=ProcessExecutionBlocked,
            message=(
                f"[TimePoll runtime guard] blocked process execution via {event}: "
                f"{_normalize_text(executable) or '<unknown>'}"
            ),
        )

    def _handle_file_event(self, event: str, args: tuple[Any, ...]) -> None:
        if len(args) < 3:
            return
        path = args[0]
        mode = args[1]
        flags = args[2]
        normalized_path = _normalize_path(path)
        if normalized_path is None:
            return
        is_write = _is_write_open(mode, flags)
        rules = (
            self.config.write_path_allow_rules
            if is_write
            else self.config.read_path_allow_rules
        )
        if any(rule.matches(normalized_path) for rule in rules):
            return
        access_kind = "write" if is_write else "read"
        self._block_or_log(
            mode=self.config.file_mode,
            error_type=FileAccessBlocked,
            message=(
                f"[TimePoll runtime guard] blocked file {access_kind} via {event}: "
                f"{normalized_path}"
            ),
        )

    def _handle_sqlite_event(self, event: str, args: tuple[Any, ...]) -> None:
        database = args[0] if args else None
        if database is None:
            return
        if any(rule.matches(database) for rule in self.config.sqlite_path_allow_rules):
            return
        self._block_or_log(
            mode=self.config.sqlite_mode,
            error_type=SQLiteConnectionBlocked,
            message=(
                f"[TimePoll runtime guard] blocked SQLite connection via {event}: "
                f"{_normalize_text(database) or '<unknown>'}"
            ),
        )

    def _block_or_log(
        self,
        *,
        mode: str,
        error_type: type[PermissionError],
        message: str,
    ) -> None:
        _emit_warning(message)
        if mode == "enforce":
            raise error_type(message)

    def _extract_destination(self, event: str, args: tuple[Any, ...]) -> tuple[str | None, int | None]:
        if event == "socket.getaddrinfo":
            if len(args) < 2:
                return None, None
            host = args[0]
            socktype = args[3] if len(args) > 3 and isinstance(args[3], int) else None
            protocol = args[4] if len(args) > 4 and isinstance(args[4], int) else None
            port = _coerce_port(args[1], socktype=socktype, protocol=protocol)
            return _coerce_address((host, port))
        if len(args) < 2:
            return None, None
        return _coerce_address(args[1])


_AUDIT_GUARD_INSTALLED = False
_ACTIVE_NETWORK_GUARD: RuntimeAuditGuard | None = None
_ORIGINAL_SOCKET_GETADDRINFO = socket.getaddrinfo
_SOCKET_GETADDRINFO_PATCHED = False


def _guarded_socket_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
    results = _ORIGINAL_SOCKET_GETADDRINFO(host, port, *args, **kwargs)
    if _ACTIVE_NETWORK_GUARD is not None:
        _ACTIVE_NETWORK_GUARD.remember_allowed_resolution(host, port, results)
    return results


def _install_guarded_socket_getaddrinfo(guard: RuntimeAuditGuard) -> None:
    global _ACTIVE_NETWORK_GUARD
    global _SOCKET_GETADDRINFO_PATCHED

    _ACTIVE_NETWORK_GUARD = guard
    if _SOCKET_GETADDRINFO_PATCHED:
        return
    socket.getaddrinfo = _guarded_socket_getaddrinfo
    _SOCKET_GETADDRINFO_PATCHED = True


def install_runtime_audit_guard() -> RuntimeAuditGuardConfig:
    global _AUDIT_GUARD_INSTALLED
    config = RuntimeAuditGuardConfig.from_env()
    config.validate_for_startup()
    if _AUDIT_GUARD_INSTALLED or not config.enabled:
        return config
    guard = RuntimeAuditGuard(config)
    if config.network_mode != "off":
        _install_guarded_socket_getaddrinfo(guard)
    sys.addaudithook(guard.handle_event)
    _AUDIT_GUARD_INSTALLED = True
    return config


def iter_allow_rules(config: RuntimeAuditGuardConfig) -> Iterable[str]:
    for rule in config.allow_rules:
        if rule.port is None:
            yield rule.host_pattern
        else:
            yield f"{rule.host_pattern}:{rule.port}"
