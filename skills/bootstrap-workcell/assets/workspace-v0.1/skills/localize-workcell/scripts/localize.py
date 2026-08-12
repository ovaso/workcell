#!/usr/bin/env python3
"""Preview, apply, and roll back auditable Workcell localizations offline."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True

OVERRIDES_RELATIVE = ".ai-workspace/localization-overrides.toml"
SNAPSHOTS_RELATIVE = ".ai-workspace/localization-snapshots"
LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Z][A-Za-z0-9]{1,7})*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PATH_TOKEN = re.compile(r"(?<![A-Za-z0-9_.-])(?:\.?/?[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9_-]+)")
URL_TOKEN = re.compile(r"https?://[^\s)>]+")
HASH_TOKEN = re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)
ID_TOKEN = re.compile(r"\b(?:[A-Z][A-Z0-9_]{2,}|[a-z][a-z0-9]+(?:-[a-z0-9]+){1,})\b")
VERSION_TOKEN = re.compile(r"\bv?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\b")
INLINE_CODE = re.compile(r"`([^`]+)`")
FENCED_BLOCK = re.compile(r"(^|\n)(```[^\n]*\n.*?\n```)(?=\n|$)", re.DOTALL)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
POLICY_TERMS = re.compile(r"\b(?:MUST NOT|MUST|SHOULD NOT|SHOULD|MAY|deny|prohibit|fail closed|authorization)\b", re.IGNORECASE)


class LocalizationError(ValueError):
    """Report an input, authorization, or preservation-contract failure."""


@dataclass(frozen=True)
class Translation:
    """Represent one selected source document and its translated counterpart."""

    relative: str
    source: Path
    target: Path
    kind: str


def portable_relative(value: str) -> bool:
    """Return whether a path is a portable, contained relative path."""

    candidate = Path(value)
    return bool(value) and not candidate.is_absolute() and ".." not in candidate.parts and "/" not in value[:1] and "\\" not in value


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 for one regular local file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    """Return a canonical UTC timestamp."""

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def toml_string(value: str) -> str:
    """Encode an arbitrary unicode string as a TOML-compatible basic string."""

    return json.dumps(value, ensure_ascii=False)


def require_workspace(root: Path) -> None:
    """Reject an ordinary directory rather than creating localization state in it."""

    required = ("AI_WORKSPACE.md", ".ai-workspace/workspace.toml", ".ai-workspace/versions.lock", ".ai-workspace/release-manifest.json")
    missing = [relative for relative in required if not (root / relative).is_file()]
    if missing:
        raise LocalizationError("Not a Workcell workspace; missing " + ", ".join(missing))


def parse_locale(value: str) -> str:
    """Require a normalized BCP-47-like locale identifier used by this workflow."""

    if not LOCALE_PATTERN.fullmatch(value):
        raise LocalizationError(f"Locale must be normalized like zh-CN or fr, got {value!r}")
    return value


def selected_sources(root: Path, scopes: set[str]) -> list[tuple[str, str]]:
    """Return selected human-readable sources, never configuration or data files."""

    if "all-readable-documents" in scopes:
        scopes = (scopes - {"all-readable-documents"}) | {"entry-documents", "standard-documents", "skill-instructions", "skill-references"}
    choices: dict[str, str] = {}
    if "entry-documents" in scopes:
        for relative in ("AI_WORKSPACE.md", "README.md"):
            if (root / relative).is_file():
                choices[relative] = "markdown"
    if "standard-documents" in scopes:
        for path in sorted((root / "docs").glob("**/*.md")) if (root / "docs").is_dir() else []:
            choices[path.relative_to(root).as_posix()] = "markdown"
    if "skill-instructions" in scopes:
        for path in sorted((root / "skills").glob("*/SKILL.md")) if (root / "skills").is_dir() else []:
            choices[path.relative_to(root).as_posix()] = "markdown"
    if "skill-references" in scopes:
        for path in sorted((root / "skills").glob("*/references/**/*.md")) if (root / "skills").is_dir() else []:
            choices[path.relative_to(root).as_posix()] = "markdown"
    if "ai-adapters" in scopes:
        for extension in ("*.yaml", "*.yml"):
            for path in sorted((root / "skills").glob(f"*/agents/{extension}")) if (root / "skills").is_dir() else []:
                choices[path.relative_to(root).as_posix()] = "adapter"
    return sorted(choices.items())


def read_text(path: Path) -> str:
    """Read UTF-8 text and reject symlink or non-regular sources."""

    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise LocalizationError(f"Refusing non-regular or symlink file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LocalizationError(f"File is not UTF-8: {path}") from exc


def stable_tokens(markdown: str) -> set[str]:
    """Extract stable tokens which a human-readable translation must retain exactly."""

    tokens: set[str] = set()
    frontmatter = FRONTMATTER.match(markdown)
    if frontmatter:
        for line in frontmatter.group(1).splitlines():
            if line.startswith("name:"):
                tokens.add(line.strip())
    tokens.update(match.group(2) for match in FENCED_BLOCK.finditer(markdown))
    tokens.update(INLINE_CODE.findall(markdown))
    tokens.update(token.rstrip(".,;:!?。，、；：！？") for token in URL_TOKEN.findall(markdown))
    tokens.update(HASH_TOKEN.findall(markdown))
    tokens.update(PATH_TOKEN.findall(markdown))
    tokens.update(ID_TOKEN.findall(markdown))
    tokens.update(VERSION_TOKEN.findall(markdown))
    tokens.update(POLICY_TERMS.findall(markdown))
    return {token for token in tokens if len(token) > 1}


def yaml_preserved_lines(source: str, translated: str) -> list[str]:
    """Return adapter changes outside the deliberately translatable scalar fields."""

    editable = {"display_name", "short_description", "default_prompt"}
    source_lines = source.splitlines()
    translated_lines = translated.splitlines()
    if len(source_lines) != len(translated_lines):
        return ["YAML line count or structure changed"]
    problems: list[str] = []
    key_pattern = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
    for number, (source_line, translated_line) in enumerate(zip(source_lines, translated_lines), start=1):
        source_match = key_pattern.match(source_line)
        translated_match = key_pattern.match(translated_line)
        if bool(source_match) != bool(translated_match):
            problems.append(f"line {number} changes YAML structure")
            continue
        if source_match is None:
            if source_line != translated_line:
                problems.append(f"line {number} is not an allowed display field")
            continue
        if source_match.group(1) != translated_match.group(1) or source_match.group(2) != translated_match.group(2):
            problems.append(f"line {number} changes YAML indentation or key")
            continue
        if source_match.group(2) not in editable and source_line != translated_line:
            problems.append(f"line {number} changes non-display key {source_match.group(2)!r}")
    return problems


def validate_translation(item: Translation) -> tuple[list[str], list[str]]:
    """Return preservation failures and policy-sensitive source paragraphs."""

    source = read_text(item.source)
    translated = read_text(item.target)
    if item.kind == "adapter":
        return yaml_preserved_lines(source, translated), []
    source_tokens = stable_tokens(source)
    translated_tokens = stable_tokens(translated)
    missing = sorted(source_tokens - translated_tokens)
    sensitive = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", source) if POLICY_TERMS.search(paragraph)]
    return [f"stable token missing: {token}" for token in missing], sensitive


def unified_diff(item: Translation) -> str:
    """Produce one concise source-to-translation unified diff."""

    return "".join(
        difflib.unified_diff(
            read_text(item.source).splitlines(keepends=True),
            read_text(item.target).splitlines(keepends=True),
            fromfile=f"source/{item.relative}",
            tofile=f"translation/{item.relative}",
        )
    )


def translated_items(root: Path, translations: Path, locale: str, mode: str, scopes: set[str]) -> tuple[list[Translation], list[str]]:
    """Pair selected sources with translation-input files using a source-relative layout."""

    missing: list[str] = []
    result: list[Translation] = []
    for relative, kind in selected_sources(root, scopes):
        source = root / relative
        candidate = translations / relative
        if not candidate.is_file():
            missing.append(relative)
            continue
        destination = root / "locales" / locale / relative if mode == "overlay" else source
        result.append(Translation(relative, source, candidate, kind))
    return result, missing


def release_context(root: Path) -> tuple[str, dict[str, str]]:
    """Read the installed release version and distribution source hashes."""

    versions = tomllib.loads((root / ".ai-workspace/versions.lock").read_text(encoding="utf-8"))
    version = versions.get("versions", {}).get("product")
    if not isinstance(version, str) or not version:
        raise LocalizationError("versions.lock has no versions.product")
    receipt = json.loads((root / ".ai-workspace/release-manifest.json").read_text(encoding="utf-8"))
    entries = receipt.get("files")
    if not isinstance(entries, list):
        raise LocalizationError("release-manifest.json has no files array")
    distribution: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("owner") == "distribution" and isinstance(entry.get("path"), str) and isinstance(entry.get("sha256"), str):
            distribution[entry["path"]] = entry["sha256"]
    return version, distribution


def load_overrides(path: Path) -> list[dict[str, Any]]:
    """Load the independent workspace-owned override registry if it exists."""

    if not path.exists():
        return []
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LocalizationError(f"Unable to parse override registry: {exc}") from exc
    entries = document.get("overrides", [])
    if document.get("schema_version") != "0.1" or not isinstance(entries, list):
        raise LocalizationError("Override registry must use schema_version 0.1 and [[overrides]] entries")
    return [entry for entry in entries if isinstance(entry, dict)]


def write_overrides(path: Path, records: list[dict[str, str]]) -> None:
    """Atomically persist the independent replacement registry in stable TOML."""

    lines = ["schema_version = \"0.1\"", ""]
    fields = ("locale", "mode", "source_release", "path", "source_sha256", "translation_sha256", "applied_at", "approval", "snapshot")
    for record in sorted(records, key=lambda entry: entry["path"]):
        lines.append("[[overrides]]")
        for field in fields:
            lines.append(f"{field} = {toml_string(record[field])}")
        lines.append("")
    atomic_write(path, "\n".join(lines))


def atomic_write(path: Path, content: str) -> None:
    """Write UTF-8 content atomically without following a target symlink."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise LocalizationError(f"Refusing to replace symlink: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".localize.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def snapshot_id(locale: str) -> str:
    """Create a sortable local snapshot identifier without external state."""

    return f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{locale}-{uuid.uuid4().hex[:8]}"


def write_snapshot(
    root: Path,
    identifier: str,
    mode: str,
    locale: str,
    items: list[Translation],
    approval: str,
    previous_overrides: list[dict[str, str]] | None = None,
) -> Path:
    """Copy pre-write files to a workspace-owned, recoverable snapshot."""

    directory = root / SNAPSHOTS_RELATIVE / identifier
    if directory.exists():
        raise LocalizationError(f"Snapshot collision: {directory}")
    records: list[dict[str, str]] = []
    try:
        for item in items:
            saved = directory / "files" / item.relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, saved, follow_symlinks=False)
            records.append({"path": item.relative, "source_sha256": sha256_file(item.source), "translation_sha256": sha256_file(item.target)})
        lines = [
            "schema_version = \"0.1\"",
            f"id = {toml_string(identifier)}",
            f"locale = {toml_string(locale)}",
            f"mode = {toml_string(mode)}",
            f"created_at = {toml_string(utc_now())}",
            f"approval = {toml_string(approval)}",
            "",
        ]
        for record in records:
            lines.append("[[files]]")
            for field in ("path", "source_sha256", "translation_sha256"):
                lines.append(f"{field} = {toml_string(record[field])}")
            lines.append("")
        atomic_write(directory / "snapshot.toml", "\n".join(lines))
        if previous_overrides is not None:
            write_overrides(directory / "overrides.toml", previous_overrides)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return directory


def write_overlay_manifest(root: Path, locale: str, items: list[Translation], missing: list[str], approval: str) -> None:
    """Record overlay source and output digests beside the subordinate locale layer."""

    lines = [
        "schema_version = \"0.1\"",
        f"locale = {toml_string(locale)}",
        'mode = "overlay"',
        f"generated_at = {toml_string(utc_now())}",
        f"approval = {toml_string(approval)}",
        "",
    ]
    for item in items:
        lines.append("[[files]]")
        lines.append(f"path = {toml_string(item.relative)}")
        lines.append(f"source_sha256 = {toml_string(sha256_file(item.source))}")
        lines.append(f"translation_sha256 = {toml_string(sha256_file(item.target))}")
        lines.append("")
    for relative in missing:
        lines.append("[[excluded]]")
        lines.append(f"path = {toml_string(relative)}")
        lines.append('reason = "translation input missing"')
        lines.append("")
    atomic_write(root / "locales" / locale / "localization.toml", "\n".join(lines))


def preview(root: Path, translations: Path | None, locale: str, mode: str, scopes: set[str]) -> dict[str, Any]:
    """Create a complete non-mutating preview suitable for operator approval."""

    selected = selected_sources(root, scopes)
    result: dict[str, Any] = {
        "schema_version": "0.1",
        "locale": locale,
        "mode": mode,
        "selected_files": [relative for relative, _ in selected],
        "excluded_by_default": ["JSON, TOML, YAML except explicitly selected AI adapters, schemas, manifests, scripts, .env, ignore files, code, credentials, logs, and evidence"],
        "files": [],
        "missing_translation_inputs": [],
        "untranslatable_items": [],
        "policy_sensitive_passages": [],
        "requires_explicit_confirmation": mode == "replace",
    }
    if translations is None:
        return result
    items, missing = translated_items(root, translations, locale, mode, scopes)
    result["missing_translation_inputs"] = missing
    for item in items:
        problems, sensitive = validate_translation(item)
        result["files"].append({"path": item.relative, "kind": item.kind, "diff": unified_diff(item), "valid": not problems})
        result["untranslatable_items"].extend({"path": item.relative, "item": problem} for problem in problems)
        result["policy_sensitive_passages"].extend({"path": item.relative, "source": paragraph} for paragraph in sensitive)
    return result


def apply(root: Path, translations: Path, locale: str, mode: str, scopes: set[str], approval: str, refresh: bool) -> dict[str, Any]:
    """Apply a reviewed translation after all preview and preservation checks pass."""

    report = preview(root, translations, locale, mode, scopes)
    if report["missing_translation_inputs"]:
        raise LocalizationError("Missing translation inputs: " + ", ".join(report["missing_translation_inputs"]))
    if report["untranslatable_items"]:
        details = "; ".join(f"{item['path']}: {item['item']}" for item in report["untranslatable_items"])
        raise LocalizationError("Translation changes protected content: " + details)
    items, _ = translated_items(root, translations, locale, mode, scopes)
    if not items:
        raise LocalizationError("No translation inputs match the selected scope")
    if mode == "overlay":
        for item in items:
            destination = root / "locales" / locale / item.relative
            if destination.exists() and not refresh:
                raise LocalizationError(f"Overlay translation already exists; use --refresh after review: {destination}")
        for item in items:
            atomic_write(root / "locales" / locale / item.relative, read_text(item.target))
        write_overlay_manifest(root, locale, items, [], approval)
        return {"mode": mode, "locale": locale, "snapshot": None, "files": [item.relative for item in items]}

    version, distribution = release_context(root)
    registry_path = root / OVERRIDES_RELATIVE
    existing = {str(entry.get("path")): entry for entry in load_overrides(registry_path)}
    for item in items:
        if item.relative not in distribution:
            raise LocalizationError(f"Replace is limited to installed distribution documents, not {item.relative}")
        if item.relative in existing and not refresh:
            raise LocalizationError(f"Replace override already exists; use --refresh after review: {item.relative}")
        if sha256_file(item.source) != distribution[item.relative] and item.relative not in existing:
            raise LocalizationError(f"Source document has unregistered distribution drift: {item.relative}")
    identifier = snapshot_id(locale)
    snapshot = write_snapshot(root, identifier, mode, locale, items, approval, list(existing.values()))
    for item in items:
        atomic_write(item.source, read_text(item.target))
    records = [entry for path, entry in existing.items() if path not in {item.relative for item in items}]
    records.extend(
        {
            "locale": locale,
            "mode": "replace",
            "source_release": version,
            "path": item.relative,
            "source_sha256": distribution[item.relative],
            "translation_sha256": sha256_file(item.source),
            "applied_at": utc_now(),
            "approval": approval,
            "snapshot": identifier,
        }
        for item in items
    )
    write_overrides(registry_path, records)
    return {"mode": mode, "locale": locale, "snapshot": snapshot.relative_to(root).as_posix(), "files": [item.relative for item in items]}


def rollback(root: Path, identifier: str, paths: set[str], approval: str) -> dict[str, Any]:
    """Restore one snapshot in whole or selected files, then clear matching overrides."""

    snapshot_root = root / SNAPSHOTS_RELATIVE / identifier
    manifest_path = snapshot_root / "snapshot.toml"
    if not manifest_path.is_file():
        raise LocalizationError(f"Snapshot does not exist: {identifier}")
    document = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "0.1" or document.get("id") != identifier:
        raise LocalizationError("Snapshot metadata is invalid")
    files = document.get("files")
    if not isinstance(files, list):
        raise LocalizationError("Snapshot contains no files")
    available = {entry.get("path") for entry in files if isinstance(entry, dict) and isinstance(entry.get("path"), str)}
    wanted = available if not paths else paths
    unknown = wanted - available
    if unknown:
        raise LocalizationError("Snapshot has no selected file: " + ", ".join(sorted(unknown)))
    for relative in sorted(wanted):
        source = snapshot_root / "files" / relative
        destination = root / relative
        if not portable_relative(relative) or not source.is_file():
            raise LocalizationError(f"Unsafe or missing snapshot file: {relative}")
        atomic_write(destination, read_text(source))
    registry_path = root / OVERRIDES_RELATIVE
    records = load_overrides(registry_path)
    previous_registry = load_overrides(snapshot_root / "overrides.toml") if (snapshot_root / "overrides.toml").is_file() else []
    retained = [record for record in records if record.get("path") not in wanted]
    retained.extend(record for record in previous_registry if record.get("path") in wanted)
    if registry_path.exists():
        write_overrides(registry_path, retained)
    return {"snapshot": identifier, "restored_files": sorted(wanted), "approval": approval}


def parser() -> argparse.ArgumentParser:
    """Build the dependency-free command-line interface."""

    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("preview", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", required=True, type=Path)
        command.add_argument("--locale", required=True)
        command.add_argument("--mode", choices=("overlay", "replace"), default="overlay")
        command.add_argument("--scope", action="append", choices=("entry-documents", "standard-documents", "skill-instructions", "skill-references", "ai-adapters", "all-readable-documents"), required=True)
        command.add_argument("--translations", type=Path)
        command.add_argument("--json", action="store_true")
    apply_command = commands.choices["apply"]
    apply_command.add_argument("--apply", action="store_true", help="Confirm the reviewed write operation")
    apply_command.add_argument("--confirm-replace", action="store_true", help="Required in replace mode")
    apply_command.add_argument("--approval", help="Approval record included in audit metadata")
    apply_command.add_argument("--refresh", action="store_true", help="Replace an existing reviewed translation after a new preview")
    rollback_command = commands.add_parser("rollback")
    rollback_command.add_argument("--workspace", required=True, type=Path)
    rollback_command.add_argument("--snapshot", required=True)
    rollback_command.add_argument("--path", action="append", default=[])
    rollback_command.add_argument("--apply", action="store_true")
    rollback_command.add_argument("--confirm-rollback", action="store_true")
    rollback_command.add_argument("--approval", required=True)
    rollback_command.add_argument("--json", action="store_true")
    return cli


def main(argv: list[str] | None = None) -> int:
    """Execute a strictly preview-first localization lifecycle."""

    arguments = parser().parse_args(argv)
    try:
        root = arguments.workspace.resolve()
        require_workspace(root)
        if arguments.command == "rollback":
            if not arguments.apply or not arguments.confirm_rollback:
                raise LocalizationError("Rollback requires --apply and --confirm-rollback")
            result = rollback(root, arguments.snapshot, set(arguments.path), arguments.approval)
        else:
            locale = parse_locale(arguments.locale)
            translations = arguments.translations.resolve() if arguments.translations else None
            if translations is not None and not translations.is_dir():
                raise LocalizationError(f"Translation input directory does not exist: {translations}")
            if arguments.command == "preview":
                result = preview(root, translations, locale, arguments.mode, set(arguments.scope))
            else:
                if not arguments.apply or not arguments.approval:
                    raise LocalizationError("Apply requires --apply and a non-empty --approval record")
                if arguments.mode == "replace" and not arguments.confirm_replace:
                    raise LocalizationError("Replace requires --confirm-replace after reviewing the preview")
                if translations is None:
                    raise LocalizationError("Apply requires --translations")
                result = apply(root, translations, locale, arguments.mode, set(arguments.scope), arguments.approval, arguments.refresh)
        if getattr(arguments, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LocalizationError, OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"localize-workcell: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
