#!/usr/bin/env python3
"""Compare current and candidate Releases with workspace files, read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


OWNERS = {"distribution", "generated", "workspace"}
SCHEMA_VERSION = "0.1"
RECEIPT_PATH = ".ai-workspace/release-manifest.json"
RELEASE_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class ManifestEntry:
    """Represent a release-file entry that passed basic format validation."""

    path: str
    owner: str
    sha256: str


@dataclass(frozen=True)
class Action:
    """Represent one file action or conflict produced by the preview."""

    path: str
    action: str
    owner: str
    reason: str


class UpgradePreviewError(ValueError):
    """Indicate that a manifest, path, or candidate fails safe-preview rules."""


def is_safe_relative_path(value: str) -> bool:
    """Return whether a path is POSIX-relative with no empty, dot, or parent segment."""

    path = Path(value)
    segments = value.split("/")
    return (
        bool(value)
        and "\\" not in value
        and not path.is_absolute()
        and all(segment not in {"", ".", ".."} for segment in segments)
    )


def sha256_file(path: Path) -> str:
    """Compute a regular file's SHA-256 by streaming."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> tuple[str, dict[str, ManifestEntry]]:
    """Parse and validate release manifest version, paths, owners, and hashes."""

    if path.is_symlink() or not path.is_file():
        raise UpgradePreviewError(f"Manifest must be a regular file: {path}")
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpgradePreviewError(f"Unable to read manifest {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise UpgradePreviewError(f"Manifest root must be an object: {path}")
    if set(document) != {"schema_version", "release_version", "files"}:
        raise UpgradePreviewError(f"Manifest fields must be exactly schema_version, release_version, and files: {path}")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise UpgradePreviewError(f"Manifest schema_version must be {SCHEMA_VERSION}: {path}")
    version = document.get("release_version")
    files = document.get("files")
    if not isinstance(version, str) or not RELEASE_VERSION_PATTERN.fullmatch(version):
        raise UpgradePreviewError(f"Manifest release_version is invalid: {path}")
    if not isinstance(files, list) or not files:
        raise UpgradePreviewError(f"Manifest files must be a non-empty array: {path}")
    entries: dict[str, ManifestEntry] = {}
    for index, raw in enumerate(files):
        if not isinstance(raw, dict):
            raise UpgradePreviewError(f"files[{index}] must be an object: {path}")
        if set(raw) != {"path", "owner", "sha256"}:
            raise UpgradePreviewError(f"files[{index}] fields must be exactly path, owner, and sha256: {path}")
        relative = raw.get("path")
        owner = raw.get("owner")
        checksum = raw.get("sha256")
        if not isinstance(relative, str) or not is_safe_relative_path(relative):
            raise UpgradePreviewError(f"files[{index}] has an unsafe path: {relative!r}")
        if relative == RECEIPT_PATH:
            raise UpgradePreviewError(f"Release manifest must not hash itself: {relative}")
        if relative in entries:
            raise UpgradePreviewError(f"Duplicate manifest path: {relative}")
        if owner not in OWNERS:
            raise UpgradePreviewError(f"File {relative} has an invalid owner: {owner!r}")
        if not isinstance(checksum, str) or len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
            raise UpgradePreviewError(f"File {relative} has an invalid sha256")
        entries[relative] = ManifestEntry(relative, owner, checksum)
    return version, entries


def actual_hash(path: Path) -> str | None:
    """Return a regular-file hash, None if absent, and fail on other types."""

    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        return "<non-regular-file>"
    return sha256_file(path)


def list_candidate_files(candidate_root: Path) -> set[str]:
    """List candidate regular files and treat the excluded receipt separately."""

    files: set[str] = set()
    for directory, directory_names, file_names in os.walk(candidate_root, followlinks=False):
        directory_names.sort(key=lambda value: value.encode("utf-8"))
        file_names.sort(key=lambda value: value.encode("utf-8"))
        directory_path = Path(directory)
        for directory_name in directory_names:
            child = directory_path / directory_name
            if child.is_symlink():
                raise UpgradePreviewError(f"Candidate Release contains a symlink directory: {child.relative_to(candidate_root).as_posix()}")
        for file_name in file_names:
            file_path = directory_path / file_name
            relative = file_path.relative_to(candidate_root).as_posix()
            mode = file_path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise UpgradePreviewError(f"Candidate Release contains a symlink file: {relative}")
            if not stat.S_ISREG(mode):
                raise UpgradePreviewError(f"Candidate Release contains a special file: {relative}")
            if relative != RECEIPT_PATH:
                files.add(relative)
    return files


def verify_candidate(candidate_root: Path, entries: dict[str, ManifestEntry]) -> None:
    """Confirm candidate regular files exactly match the manifest and hashes."""

    actual_files = list_candidate_files(candidate_root)
    manifest_files = set(entries)
    missing = sorted(manifest_files - actual_files)
    extra = sorted(actual_files - manifest_files)
    if missing:
        raise UpgradePreviewError(f"Candidate file is missing: {missing[0]}")
    if extra:
        raise UpgradePreviewError(f"Candidate has a file not listed in the Release manifest: {extra[0]}")

    for entry in entries.values():
        path = candidate_root / entry.path
        checksum = actual_hash(path)
        if checksum is None:
            raise UpgradePreviewError(f"Candidate file is missing: {entry.path}")
        if checksum != entry.sha256:
            raise UpgradePreviewError(f"Candidate file hash mismatch: {entry.path}")


def preview_upgrade(
    workspace: Path,
    current_manifest: Path,
    candidate_root: Path,
    candidate_manifest: Path,
) -> dict[str, Any]:
    """Generate an upgrade file-action plan without modifying the workspace."""

    workspace = workspace.resolve()
    candidate_root = candidate_root.resolve()
    if not workspace.is_dir():
        raise UpgradePreviewError(f"Workspace does not exist: {workspace}")
    if not candidate_root.is_dir():
        raise UpgradePreviewError(f"Candidate directory does not exist: {candidate_root}")
    current_version, current = load_manifest(current_manifest)
    candidate_version, candidate = load_manifest(candidate_manifest)
    installed_receipt = workspace / RECEIPT_PATH
    candidate_receipt = candidate_root / RECEIPT_PATH
    if installed_receipt.is_symlink() or not installed_receipt.is_file():
        raise UpgradePreviewError(f"Current workspace lacks a regular installed receipt: {RECEIPT_PATH}")
    if candidate_receipt.is_symlink() or not candidate_receipt.is_file():
        raise UpgradePreviewError(f"Candidate Release lacks a regular installed receipt: {RECEIPT_PATH}")
    if installed_receipt.read_bytes() != current_manifest.read_bytes():
        raise UpgradePreviewError("--current-manifest does not match the installed workspace receipt")
    if candidate_receipt.read_bytes() != candidate_manifest.read_bytes():
        raise UpgradePreviewError("--candidate-manifest does not match the candidate Release receipt")
    verify_candidate(candidate_root, candidate)

    actions: list[Action] = []
    all_paths = sorted(set(current) | set(candidate))
    for relative in all_paths:
        old = current.get(relative)
        new = candidate.get(relative)
        target_hash = actual_hash(workspace / relative)

        if old is not None and new is not None and old.owner != new.owner:
            actions.append(Action(relative, "conflict", new.owner, f"Ownership changes from {old.owner} to {new.owner}; an explicit Migration is required"))
            continue

        if new is not None and new.owner == "workspace":
            action = "preserve" if target_hash is not None else "offer-seed"
            actions.append(Action(relative, action, new.owner, "Workspace-owned content must not be overwritten by a Release upgrade"))
            continue

        if new is not None and new.owner == "generated":
            actions.append(Action(relative, "regenerate", new.owner, "Regenerate from upgraded structured sources of truth"))
            continue

        if old is None and new is not None:
            if target_hash is None:
                actions.append(Action(relative, "add", new.owner, "Add new release file"))
            else:
                actions.append(Action(relative, "conflict", new.owner, "Target path is occupied by unknown existing content"))
            continue

        if old is not None and new is None:
            if old.owner == "workspace":
                actions.append(Action(relative, "preserve", old.owner, "Preserve workspace file even when removed from the candidate manifest"))
            elif old.owner == "generated":
                actions.append(Action(relative, "regenerate", old.owner, "Let the new-version generator decide whether to retain it") )
            elif target_hash is None:
                actions.append(Action(relative, "unchanged", old.owner, "Old release file is already absent"))
            elif target_hash == old.sha256:
                actions.append(Action(relative, "remove", old.owner, "Candidate removes an unmodified old release file"))
            else:
                actions.append(Action(relative, "conflict", old.owner, "Old release file to remove has local changes or a type change"))
            continue

        if old is None or new is None:
            raise AssertionError("Path-set branch is incomplete")
        if target_hash is None:
            actions.append(Action(relative, "conflict", new.owner, "Current release file is missing; restoration cannot be decided safely"))
        elif target_hash != old.sha256:
            actions.append(Action(relative, "conflict", new.owner, "Current release file does not match the installed hash"))
        elif old.sha256 == new.sha256:
            actions.append(Action(relative, "unchanged", new.owner, "Candidate content is unchanged"))
        else:
            actions.append(Action(relative, "replace", new.owner, "Replace a release file that has no local modification"))

    if installed_receipt.read_bytes() == candidate_receipt.read_bytes():
        actions.append(Action(RECEIPT_PATH, "unchanged", "distribution", "Installed receipt is unchanged"))
    else:
        actions.append(
            Action(
                RECEIPT_PATH,
                "replace-receipt",
                "distribution",
                "Replace atomically last after every upgrade gate succeeds; the receipt does not hash itself",
            )
        )

    conflicts = [action for action in actions if action.action == "conflict"]
    counts: dict[str, int] = {}
    for action in actions:
        counts[action.action] = counts.get(action.action, 0) + 1
    return {
        "current_version": current_version,
        "candidate_version": candidate_version,
        "safe_to_apply": not conflicts,
        "counts": counts,
        "actions": [asdict(action) for action in actions],
        "conflicts": [asdict(action) for action in conflicts],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse explicit path arguments required for a safe preview."""

    parser = argparse.ArgumentParser(description="Preview Standard Workspace upgrade file impact read-only")
    parser.add_argument("--workspace", required=True, help="Current Standard Workspace root")
    parser.add_argument("--current-manifest", required=True, help="Currently installed Release manifest")
    parser.add_argument("--candidate-root", required=True, help="Validated candidate Release root")
    parser.add_argument("--candidate-manifest", required=True, help="Candidate Release manifest")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the preview and distinguish safe, conflicting, and invalid input by exit code."""

    args = parse_args(argv or sys.argv[1:])
    try:
        result = preview_upgrade(
            Path(args.workspace),
            Path(args.current_manifest),
            Path(args.candidate_root),
            Path(args.candidate_manifest),
        )
    except UpgradePreviewError as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, ensure_ascii=False, indent=2) if args.json else f"INVALID: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['current_version']} -> {result['candidate_version']} safe_to_apply={result['safe_to_apply']}")
        for action in result["actions"]:
            print(f"[{action['action']}] {action['path']}: {action['reason']}")
    return 0 if result["safe_to_apply"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
