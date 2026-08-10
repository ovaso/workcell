#!/usr/bin/env python3
"""Validate and canonicalize a Workcell project plugin candidate."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "0.1"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_REPOSITORY_MODELS = {"single", "monorepo", "multi"}
ALLOWED_ROLES = {"edit", "verify", "reference"}
ALLOWED_FACT_SOURCES = {"declared", "discovered", "derived", "runtime"}
ALLOWED_POLICY_SOURCES = {"user-confirmed", "workspace-policy", "project-config", "project-rule"}
WORKFLOW_NAMES = {"build", "test", "verify", "review", "release", "rollback", "close"}
SENSITIVE_KEY_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
    "api_key",
)


class ValidationError(ValueError):
    """Report a deterministic project plugin validation failure."""


def require_object(value: Any, location: str) -> dict[str, Any]:
    """Return a JSON object or raise a location-aware error."""

    if not isinstance(value, dict):
        raise ValidationError(f"{location} must be an object")
    return value


def require_list(value: Any, location: str) -> list[Any]:
    """Return a JSON array or raise a location-aware error."""

    if not isinstance(value, list):
        raise ValidationError(f"{location} must be an array")
    return value


def require_string(value: Any, location: str) -> str:
    """Return a non-empty string or raise a location-aware error."""

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{location} must be a non-empty string")
    return value


def require_id(value: Any, location: str) -> str:
    """Validate a portable lowercase hyphenated identifier."""

    identifier = require_string(value, location)
    if not ID_PATTERN.fullmatch(identifier):
        raise ValidationError(f"{location} must use lowercase letters, digits, and hyphens")
    return identifier


def require_relative_path(value: Any, location: str) -> str:
    """Reject host-specific absolute paths and parent traversal."""

    rendered = require_string(value, location).replace("\\", "/")
    path = PurePosixPath(rendered)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:/", rendered):
        raise ValidationError(f"{location} must be a relative logical path without '..'")
    return rendered


def ensure_unique_ids(items: list[Any], location: str) -> set[str]:
    """Validate object IDs and return the unique set."""

    identifiers: set[str] = set()
    for index, item in enumerate(items):
        obj = require_object(item, f"{location}[{index}]")
        identifier = require_id(obj.get("id"), f"{location}[{index}].id")
        if identifier in identifiers:
            raise ValidationError(f"duplicate id {identifier!r} in {location}")
        identifiers.add(identifier)
    return identifiers


def reject_sensitive_content(value: Any, location: str = "root") -> None:
    """Reject credential-like fields and credential-bearing URLs."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower()
            if any(marker in normalized for marker in SENSITIVE_KEY_MARKERS) and not normalized.endswith(
                ("_ref", "_name")
            ):
                raise ValidationError(f"credential-like field is not allowed at {location}.{key}")
            reject_sensitive_content(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_content(child, f"{location}[{index}]")
    elif isinstance(value, str):
        if re.search(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s@]+@", value):
            raise ValidationError(f"credential-bearing URL is not allowed at {location}")


def validate_workflows(workflows: dict[str, Any]) -> None:
    """Validate known workflow arrays and shell-free argv commands."""

    unknown = set(workflows) - WORKFLOW_NAMES
    if unknown:
        raise ValidationError(f"unknown workflow sections: {', '.join(sorted(unknown))}")
    workflow_ids: set[str] = set()
    for name in sorted(WORKFLOW_NAMES):
        entries = require_list(workflows.get(name, []), f"workflows.{name}")
        for index, entry in enumerate(entries):
            obj = require_object(entry, f"workflows.{name}[{index}]")
            identifier = require_id(obj.get("id"), f"workflows.{name}[{index}].id")
            if identifier in workflow_ids:
                raise ValidationError(f"duplicate workflow id {identifier!r}")
            workflow_ids.add(identifier)
            require_relative_path(
                obj.get("working_directory", "."),
                f"workflows.{name}[{index}].working_directory",
            )
            argv = require_list(obj.get("argv"), f"workflows.{name}[{index}].argv")
            if not argv:
                raise ValidationError(f"workflows.{name}[{index}].argv must not be empty")
            for argument_index, argument in enumerate(argv):
                require_string(argument, f"workflows.{name}[{index}].argv[{argument_index}]")


def validate_evidence(candidate: dict[str, Any]) -> None:
    """Validate facts, inferences, policies, and unresolved questions."""

    facts = require_list(candidate.get("facts", []), "facts")
    fact_ids = ensure_unique_ids(facts, "facts")
    for index, item in enumerate(facts):
        obj = require_object(item, f"facts[{index}]")
        source_type = require_string(obj.get("source_type"), f"facts[{index}].source_type")
        if source_type not in ALLOWED_FACT_SOURCES:
            raise ValidationError(f"facts[{index}].source_type is invalid")
        for field in ("kind", "source", "observed_at", "context", "confidence", "sensitivity"):
            require_string(obj.get(field), f"facts[{index}].{field}")

    inferences = require_list(candidate.get("inferences", []), "inferences")
    ensure_unique_ids(inferences, "inferences")
    for index, item in enumerate(inferences):
        obj = require_object(item, f"inferences[{index}]")
        require_string(obj.get("statement"), f"inferences[{index}].statement")
        references = require_list(obj.get("fact_refs"), f"inferences[{index}].fact_refs")
        if not references:
            raise ValidationError(f"inferences[{index}].fact_refs must not be empty")
        missing = {require_string(ref, f"inferences[{index}].fact_refs") for ref in references} - fact_ids
        if missing:
            raise ValidationError(f"inferences[{index}] references unknown facts: {sorted(missing)}")
        require_string(obj.get("confidence"), f"inferences[{index}].confidence")

    policies = require_list(candidate.get("policies", []), "policies")
    ensure_unique_ids(policies, "policies")
    for index, item in enumerate(policies):
        obj = require_object(item, f"policies[{index}]")
        require_string(obj.get("statement"), f"policies[{index}].statement")
        source_type = require_string(obj.get("source_type"), f"policies[{index}].source_type")
        if source_type not in ALLOWED_POLICY_SOURCES:
            raise ValidationError(f"policies[{index}].source_type must identify a confirmed policy source")

    questions = require_list(candidate.get("unresolved_questions", []), "unresolved_questions")
    ensure_unique_ids(questions, "unresolved_questions")
    for index, item in enumerate(questions):
        require_string(
            require_object(item, f"unresolved_questions[{index}]").get("question"),
            f"unresolved_questions[{index}].question",
        )


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete project plugin candidate."""

    reject_sensitive_content(candidate)
    if candidate.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION!r}")

    plugin = require_object(candidate.get("plugin"), "plugin")
    require_id(plugin.get("id"), "plugin.id")
    for field in ("display_name", "version", "api_version"):
        require_string(plugin.get(field), f"plugin.{field}")
    repository_model = require_string(plugin.get("repository_model"), "plugin.repository_model")
    if repository_model not in ALLOWED_REPOSITORY_MODELS:
        raise ValidationError(f"plugin.repository_model must be one of {sorted(ALLOWED_REPOSITORY_MODELS)}")

    repositories = require_list(candidate.get("repositories"), "repositories")
    if not repositories:
        raise ValidationError("repositories must not be empty")
    repository_ids = ensure_unique_ids(repositories, "repositories")
    for index, item in enumerate(repositories):
        obj = require_object(item, f"repositories[{index}]")
        require_relative_path(obj.get("path"), f"repositories[{index}].path")
        require_string(obj.get("default_branch"), f"repositories[{index}].default_branch")
    if repository_model == "single" and len(repositories) != 1:
        raise ValidationError("single repository_model requires exactly one repository")

    modules = require_list(candidate.get("modules"), "modules")
    if not modules:
        raise ValidationError("modules must not be empty")
    ensure_unique_ids(modules, "modules")
    for index, item in enumerate(modules):
        obj = require_object(item, f"modules[{index}]")
        repository = require_id(obj.get("repository"), f"modules[{index}].repository")
        if repository not in repository_ids:
            raise ValidationError(f"modules[{index}] references unknown repository {repository!r}")
        require_relative_path(obj.get("path"), f"modules[{index}].path")
        role = require_string(obj.get("role"), f"modules[{index}].role")
        if role not in ALLOWED_ROLES:
            raise ValidationError(f"modules[{index}].role must be one of {sorted(ALLOWED_ROLES)}")
        adapters = require_list(obj.get("technology_adapters", []), f"modules[{index}].technology_adapters")
        for adapter_index, adapter in enumerate(adapters):
            require_id(adapter, f"modules[{index}].technology_adapters[{adapter_index}]")

    validate_workflows(require_object(candidate.get("workflows", {}), "workflows"))
    for collection in ("risk_areas", "knowledge"):
        ensure_unique_ids(require_list(candidate.get(collection, []), collection), collection)
    capabilities = require_object(candidate.get("capabilities", {"enabled": []}), "capabilities")
    enabled = require_list(capabilities.get("enabled", []), "capabilities.enabled")
    for index, capability in enumerate(enabled):
        require_id(capability, f"capabilities.enabled[{index}]")
    validate_evidence(candidate)
    return candidate


def canonical_json(candidate: dict[str, Any]) -> str:
    """Return deterministic UTF-8 JSON after validation."""

    validate_candidate(candidate)
    return json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_output(rendered: str, output: str, force: bool) -> None:
    """Print canonical JSON or atomically write an approved destination."""

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
    """Parse deterministic builder arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="-")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate, canonicalize, and optionally persist a project plugin."""

    try:
        args = parse_args(argv)
        source = Path(args.input).expanduser().resolve()
        candidate = require_object(json.loads(source.read_text(encoding="utf-8")), "root")
        write_output(canonical_json(candidate), args.output, args.force)
        return 0
    except (OSError, json.JSONDecodeError, ValidationError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
