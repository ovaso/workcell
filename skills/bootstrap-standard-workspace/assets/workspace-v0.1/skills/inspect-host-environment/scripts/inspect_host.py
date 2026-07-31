#!/usr/bin/env python3
"""Collect read-only host facts without persisting environment variable values."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


SCHEMA_VERSION = "0.1"
ALLOWED_CONTEXTS = (
    "system",
    "login-shell",
    "non-interactive-shell",
    "ai-execution",
    "workspace",
    "project",
    "task",
)
DEFAULT_COMMANDS = (
    "git",
    "python3",
    "python",
    "node",
    "java",
    "javac",
    "mvn",
    "gradle",
    "go",
    "rustc",
    "cargo",
    "dotnet",
    "ruby",
    "php",
    "docker",
    "podman",
    "kubectl",
    "make",
    "cmake",
    "ninja",
    "mise",
    "asdf",
)
VERSION_ARGUMENTS = {
    "git": ("--version",),
    "python3": ("--version",),
    "python": ("--version",),
    "node": ("--version",),
    "java": ("-version",),
    "javac": ("-version",),
    "mvn": ("--version",),
    "gradle": ("--version",),
    "go": ("version",),
    "rustc": ("--version",),
    "cargo": ("--version",),
    "dotnet": ("--version",),
    "ruby": ("--version",),
    "php": ("--version",),
    "docker": ("--version",),
    "podman": ("--version",),
    "kubectl": ("version", "--client"),
    "make": ("--version",),
    "cmake": ("--version",),
    "ninja": ("--version",),
    "mise": ("--version",),
    "asdf": ("--version",),
}
TOOLCHAIN_KINDS = {
    "python3": "python",
    "python": "python",
    "node": "nodejs",
    "java": "java-runtime",
    "javac": "java-compiler",
    "mvn": "maven",
    "gradle": "gradle",
    "go": "go",
    "rustc": "rust",
    "cargo": "rust-cargo",
    "dotnet": "dotnet",
    "ruby": "ruby",
    "php": "php",
}
SECRET_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
    "api_key",
    "cookie",
    "session",
    "bearer",
    "auth",
)
PRIVATE_MARKERS = (
    "user",
    "email",
    "home",
    "path",
    "host",
    "endpoint",
    "proxy",
    "account",
    "tenant",
    "project",
    "organization",
    "region",
)
PUBLIC_ENV_NAMES = {
    "CI",
    "COLORTERM",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "OS",
    "TERM",
    "TZ",
}


def utc_now() -> str:
    """Return a stable UTC timestamp without fractional seconds."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_command_name(name: str) -> str:
    """Accept executable names without shell syntax or path traversal."""

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", name):
        raise ValueError(f"invalid command name: {name!r}")
    return name


def first_meaningful_line(output: str) -> str | None:
    """Return a bounded first non-empty line from version output."""

    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:500]
    return None


def inspect_command(name: str, context: str, observed_at: str, timeout: float) -> dict[str, Any]:
    """Resolve a command and run only a known read-only version probe."""

    validate_command_name(name)
    path = shutil.which(name)
    fact: dict[str, Any] = {
        "id": f"command:{context}:{name}",
        "kind": "command",
        "source_type": "discovered",
        "source": "process PATH resolution",
        "observed_at": observed_at,
        "context": context,
        "confidence": "high",
        "sensitivity": "private",
        "name": name,
        "available": path is not None,
        "resolved_path": path,
        "version": None,
        "version_probe": "not-available" if path is None else "unsupported",
    }
    arguments = VERSION_ARGUMENTS.get(name)
    if path is None or arguments is None:
        return fact

    try:
        completed = subprocess.run(
            [path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        fact["version"] = first_meaningful_line(combined)
        fact["version_probe"] = "completed" if fact["version"] else "empty-output"
        fact["version_probe_exit_code"] = completed.returncode
        fact["version_probe_argv"] = [name, *arguments]
    except subprocess.TimeoutExpired:
        fact["version_probe"] = "timeout"
        fact["version_probe_argv"] = [name, *arguments]
    except OSError as exc:
        fact["version_probe"] = "error"
        fact["version_probe_error"] = type(exc).__name__
    return fact


def derive_toolchain_fact(command_fact: dict[str, Any]) -> dict[str, Any] | None:
    """Create a toolchain fact only from a resolved known runtime command."""

    name = command_fact["name"]
    if not command_fact["available"] or name not in TOOLCHAIN_KINDS:
        return None
    return {
        "id": f"toolchain:{command_fact['context']}:{TOOLCHAIN_KINDS[name]}:{name}",
        "kind": "toolchain",
        "source_type": "derived",
        "source": command_fact["id"],
        "observed_at": command_fact["observed_at"],
        "context": command_fact["context"],
        "confidence": "high",
        "sensitivity": "private",
        "toolchain": TOOLCHAIN_KINDS[name],
        "command": name,
        "declared_version": None,
        "installed_versions": [],
        "current_version": command_fact.get("version"),
        "manager": "unknown",
        "scope": command_fact["context"],
    }


def classify_env_name(name: str) -> tuple[str, str]:
    """Classify a variable name without examining its value."""

    normalized = name.lower()
    if any(marker in normalized for marker in SECRET_MARKERS):
        return "secret", "credential-like-name"
    if any(marker in normalized for marker in PRIVATE_MARKERS):
        return "private", "identity-path-or-endpoint-name"
    if name.upper() in PUBLIC_ENV_NAMES:
        return "public", "explicit-safe-name"
    return "secret", "unknown-defaults-to-secret"


def inspect_environment_name(name: str, context: str, observed_at: str) -> dict[str, Any]:
    """Record only the variable name and presence, never its value."""

    sensitivity, classification_source = classify_env_name(name)
    return {
        "id": f"environment-variable:{context}:{name}",
        "kind": "environment-variable",
        "source_type": "runtime",
        "source": "current process environment name table",
        "observed_at": observed_at,
        "context": context,
        "confidence": "high",
        "sensitivity": sensitivity,
        "name": name,
        "is_set": name in os.environ,
        "value_recorded": False,
        "classification_source": classification_source,
    }


def sanitize_network_target(target: str) -> tuple[str, str]:
    """Validate and canonicalize an explicitly declared network target."""

    parsed = parse.urlsplit(target)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https", "tcp"}:
        raise ValueError(f"unsupported network scheme: {scheme or '<missing>'}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("network target must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("network target must not contain a query string or fragment")
    if not parsed.hostname:
        raise ValueError("network target must include a host")
    if "*" in parsed.hostname:
        raise ValueError("network target must not contain wildcards")
    if scheme == "tcp" and parsed.port is None:
        raise ValueError("tcp target must include an explicit port")

    host = parsed.hostname.lower()
    rendered_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    port = f":{parsed.port}" if parsed.port is not None else ""
    path = parsed.path or ("/" if scheme in {"http", "https"} else "")
    canonical = parse.urlunsplit((scheme, f"{rendered_host}{port}", path, "", ""))
    return scheme, canonical


class NoRedirectHandler(request.HTTPRedirectHandler):
    """Prevent probes from leaving the explicitly approved target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def probe_network_target(target: str, timeout: float) -> dict[str, Any]:
    """Probe one already validated target without redirects."""

    scheme, canonical = sanitize_network_target(target)
    if scheme == "tcp":
        parsed = parse.urlsplit(canonical)
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=timeout):
                return {"status": "reachable", "connection_result": "connected"}
        except OSError as exc:
            return {"status": "unreachable", "connection_result": type(exc).__name__}

    opener = request.build_opener(NoRedirectHandler())
    probe_request = request.Request(canonical, method="HEAD", headers={"User-Agent": "standard-workspace/0.1"})
    try:
        with opener.open(probe_request, timeout=timeout) as response:
            return {"status": "reachable", "response_code": response.status, "method": "HEAD"}
    except error.HTTPError as exc:
        return {"status": "reachable", "response_code": exc.code, "method": "HEAD"}
    except (error.URLError, TimeoutError, OSError) as exc:
        return {"status": "unreachable", "error": type(exc).__name__, "method": "HEAD"}


def network_fact(
    target: str,
    context: str,
    observed_at: str,
    timeout: float,
    probe: bool,
    ttl_seconds: int,
) -> dict[str, Any]:
    """Create a declared or runtime fact for one exact target."""

    scheme, canonical = sanitize_network_target(target)
    fact: dict[str, Any] = {
        "id": f"network:{context}:{canonical}",
        "kind": "network",
        "source_type": "runtime" if probe else "declared",
        "source": "explicit command-line target",
        "observed_at": observed_at,
        "context": context,
        "confidence": "high",
        "sensitivity": "private",
        "protocol": scheme,
        "target_reference": canonical,
        "status": "declared-not-probed",
        "ttl_seconds": ttl_seconds if probe else 0,
    }
    if probe:
        fact.update(probe_network_target(canonical, timeout))
    return fact


def build_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    """Build a fact-only snapshot from parsed arguments."""

    observed_at = utc_now()
    command_names = list(args.command)
    if not args.no_default_commands:
        command_names.extend(DEFAULT_COMMANDS)
    command_names = sorted({validate_command_name(name) for name in command_names})

    commands = [inspect_command(name, args.context, observed_at, args.timeout) for name in command_names]
    toolchains = [fact for fact in (derive_toolchain_fact(item) for item in commands) if fact is not None]

    environment_names: list[str]
    if args.skip_environment_names:
        environment_names = []
    elif args.env_name:
        environment_names = sorted(set(args.env_name))
    else:
        environment_names = sorted(os.environ)

    network = [
        network_fact(
            target,
            args.context,
            observed_at,
            args.timeout,
            args.probe_network,
            args.network_ttl_seconds,
        )
        for target in args.network_target
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot": {
            "id": f"host-{observed_at.replace(':', '').replace('-', '')}",
            "observed_at": observed_at,
            "context": args.context,
            "status": args.status,
            "collector": "inspect-host-environment/scripts/inspect_host.py",
            "network_probe_requested": bool(args.probe_network),
        },
        "facts": {
            "commands": commands,
            "toolchains": toolchains,
            "environment_variables": [
                inspect_environment_name(name, args.context, observed_at) for name in environment_names
            ],
            "network": network,
        },
    }


def write_json(payload: dict[str, Any], output: str, force: bool) -> None:
    """Print JSON or atomically write an explicitly selected path."""

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(rendered)
        return

    destination = Path(output).expanduser().resolve()
    if destination.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing file: {destination}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {destination.parent}")

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse collector arguments without accepting arbitrary shell fragments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", choices=ALLOWED_CONTEXTS, default="ai-execution")
    parser.add_argument("--status", choices=("verified", "degraded"), default="verified")
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--no-default-commands", action="store_true")
    parser.add_argument("--env-name", action="append", default=[])
    parser.add_argument("--skip-environment-names", action="store_true")
    parser.add_argument("--network-target", action="append", default=[])
    parser.add_argument("--probe-network", action="store_true")
    parser.add_argument("--network-ttl-seconds", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--output", default="-")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.network_ttl_seconds <= 0:
        parser.error("--network-ttl-seconds must be positive")
    if args.probe_network and not args.network_target:
        parser.error("--probe-network requires at least one --network-target")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the collector and return a process exit code."""

    try:
        args = parse_args(argv)
        write_json(build_snapshot(args), args.output, args.force)
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
