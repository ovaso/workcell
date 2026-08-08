#!/usr/bin/env python3
"""Generate a deterministic installed-Release integrity manifest for workspace assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "0.1"
MANIFEST_PATH = ".ai-workspace/release-manifest.json"
OWNERS = {"distribution", "generated", "workspace"}
RELEASE_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


class ReleaseManifestError(ValueError):
    """Indicate an asset, ownership policy, or output violates the Release contract."""


@dataclass(frozen=True)
class OwnershipRule:
    """Represent an ownership rule participating in ordered first-match resolution."""

    pattern: str
    owner: str


def sha256_file(path: Path) -> str:
    """Compute a regular file's SHA-256 by streaming."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relative_pattern(pattern: str) -> None:
    """Validate V0.1 ownership patterns as safe exact paths or trailing directory globs."""

    if not pattern or pattern.startswith("/") or "\\" in pattern or "//" in pattern:
        raise ReleaseManifestError(f"Invalid ownership pattern: {pattern!r}")
    path_parts = PurePosixPath(pattern.removesuffix("/**")).parts
    if any(part in {"", ".", ".."} for part in path_parts):
        raise ReleaseManifestError(f"Ownership pattern contains an unsafe path segment: {pattern!r}")
    wildcard_count = sum(pattern.count(token) for token in ("*", "?", "["))
    if wildcard_count and (not pattern.endswith("/**") or wildcard_count != 2):
        raise ReleaseManifestError(f"V0.1 does not support this ownership wildcard: {pattern!r}")
    if pattern == "/**":
        raise ReleaseManifestError("Ownership directory wildcard must include a relative directory")


def load_ownership(path: Path) -> tuple[str, list[OwnershipRule]]:
    """Read and strictly validate the first-match ownership policy."""

    if path.is_symlink() or not path.is_file():
        raise ReleaseManifestError(f"ownership.toml must be a regular file: {path}")
    try:
        with path.open("rb") as stream:
            document: Any = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseManifestError(f"Unable to read ownership.toml: {exc}") from exc
    if not isinstance(document, dict):
        raise ReleaseManifestError("ownership.toml root must be a table")
    ownership = document.get("ownership")
    raw_rules = document.get("rules")
    if not isinstance(ownership, dict):
        raise ReleaseManifestError("ownership.toml is missing [ownership]")
    if ownership.get("version") != SCHEMA_VERSION:
        raise ReleaseManifestError("ownership.toml version must be 0.1")
    default_owner = ownership.get("default")
    if default_owner not in OWNERS:
        raise ReleaseManifestError(f"ownership.toml has an invalid default: {default_owner!r}")
    if ownership.get("resolution") != "first-match":
        raise ReleaseManifestError("ownership.toml resolution must be first-match")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ReleaseManifestError("ownership.toml rules must be a non-empty array of tables")

    rules: list[OwnershipRule] = []
    seen_patterns: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            raise ReleaseManifestError(f"rules[{index}] must be a table")
        pattern = raw_rule.get("pattern")
        owner = raw_rule.get("owner")
        if not isinstance(pattern, str):
            raise ReleaseManifestError(f"rules[{index}].pattern must be a string")
        validate_relative_pattern(pattern)
        if pattern in seen_patterns:
            raise ReleaseManifestError(f"Duplicate ownership pattern: {pattern}")
        if owner not in OWNERS:
            raise ReleaseManifestError(f"rules[{index}].owner is invalid: {owner!r}")
        seen_patterns.add(pattern)
        rules.append(OwnershipRule(pattern, owner))
    return default_owner, rules


def rule_matches(pattern: str, relative_path: str) -> bool:
    """Match according to V0.1 exact-path and `/**` directory rules."""

    if pattern.endswith("/**"):
        directory = pattern[:-3]
        return relative_path == directory or relative_path.startswith(f"{directory}/")
    return relative_path == pattern


def resolve_owner(relative_path: str, default_owner: str, rules: list[OwnershipRule]) -> str:
    """Return the first matching owner in declaration order, or the default."""

    for rule in rules:
        if rule_matches(rule.pattern, relative_path):
            return rule.owner
    return default_owner


def list_regular_files(asset_root: Path) -> list[tuple[str, Path]]:
    """List all regular asset files and reject symlinks and special files."""

    files: list[tuple[str, Path]] = []
    for directory, directory_names, file_names in os.walk(asset_root, followlinks=False):
        directory_names.sort(key=lambda value: value.encode("utf-8"))
        file_names.sort(key=lambda value: value.encode("utf-8"))
        directory_path = Path(directory)
        for directory_name in directory_names:
            child = directory_path / directory_name
            if child.is_symlink():
                raise ReleaseManifestError(f"Release asset prohibits symlink directories: {child}")
        for file_name in file_names:
            file_path = directory_path / file_name
            relative_path = file_path.relative_to(asset_root).as_posix()
            file_mode = file_path.lstat().st_mode
            if stat.S_ISLNK(file_mode):
                raise ReleaseManifestError(f"Release asset prohibits symlink files: {relative_path}")
            if not stat.S_ISREG(file_mode):
                raise ReleaseManifestError(f"Release asset prohibits special files: {relative_path}")
            if relative_path != MANIFEST_PATH:
                files.append((relative_path, file_path))
    return sorted(files, key=lambda item: item[0].encode("utf-8"))


def build_manifest(asset_root: Path, release_version: str) -> dict[str, Any]:
    """Build an in-memory Release manifest from asset files and first-match ownership."""

    if not RELEASE_VERSION_PATTERN.fullmatch(release_version):
        raise ReleaseManifestError(f"Invalid release_version: {release_version!r}")
    if asset_root.is_symlink() or not asset_root.is_dir():
        raise ReleaseManifestError(f"Asset root must be a non-symlink directory: {asset_root}")
    manifest_path = asset_root / MANIFEST_PATH
    if manifest_path.is_symlink() or (manifest_path.exists() and not manifest_path.is_file()):
        raise ReleaseManifestError(f"Release manifest path must be a regular file or absent: {manifest_path}")
    ownership_path = asset_root / ".ai-workspace/ownership.toml"
    default_owner, rules = load_ownership(ownership_path)

    entries = []
    for relative_path, file_path in list_regular_files(asset_root):
        entries.append(
            {
                "path": relative_path,
                "owner": resolve_owner(relative_path, default_owner, rules),
                "sha256": sha256_file(file_path),
            }
        )
    if not entries:
        raise ReleaseManifestError("Release asset requires at least one regular file")
    return {
        "schema_version": SCHEMA_VERSION,
        "release_version": release_version,
        "files": entries,
    }


def canonical_bytes(document: dict[str, Any]) -> bytes:
    """Encode the manifest as canonical UTF-8 bytes with fixed indentation and newline."""

    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_manifest(asset_root: Path, content: bytes) -> Path:
    """Replace the Release manifest atomically inside the asset."""

    manifest_path = asset_root / MANIFEST_PATH
    if manifest_path.is_symlink():
        raise ReleaseManifestError(f"Release manifest path must not be a symlink: {manifest_path}")
    if not manifest_path.parent.is_dir() or manifest_path.parent.is_symlink():
        raise ReleaseManifestError("Release manifest parent must be a regular directory inside the asset")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".release-manifest.", dir=manifest_path.parent, delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(0o644)
        os.replace(temporary_path, manifest_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse arguments for build or read-only validation."""

    parser = argparse.ArgumentParser(description="Generate the installed-Release integrity manifest for a Standard Workspace")
    parser.add_argument("--asset-root", required=True, help="workspace-vX.Y Release asset root")
    parser.add_argument("--release-version", required=True, help="Product version of the immutable Release")
    parser.add_argument("--check", action="store_true", help="Only verify that the existing manifest is canonical for the current asset")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Generate the manifest or check its integrity and determinism read-only."""

    args = parse_args(argv or sys.argv[1:])
    asset_root = Path(args.asset_root).absolute()
    try:
        expected = canonical_bytes(build_manifest(asset_root, args.release_version))
        manifest_path = asset_root / MANIFEST_PATH
        if args.check:
            try:
                actual = manifest_path.read_bytes()
            except OSError as exc:
                raise ReleaseManifestError(f"Unable to read existing Release manifest: {exc}") from exc
            if actual != expected:
                raise ReleaseManifestError("Existing Release manifest does not match asset files or ownership policy")
            print(f"VALID: {manifest_path}")
            return 0
        written_path = write_manifest(asset_root, expected)
        print(f"GENERATED: {written_path}")
        return 0
    except ReleaseManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
