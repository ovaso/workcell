#!/usr/bin/env python3
"""Run conservative dependency-free privacy and structure checks on feedback."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SLASH = chr(47)
BACKSLASH = chr(92)
FORBIDDEN = re.compile("|".join((SLASH + "Users" + SLASH, SLASH + "home" + SLASH + "[^" + SLASH + "]+" + SLASH, BACKSLASH * 2 + "Users" + BACKSLASH * 2, r"https?:" + SLASH * 2, r"(?:api[_-]?key|password|secret|token)\\s*[:=]")), re.I)
SCOPES = {"local", "project-plugin", "standard-candidate"}


def validate(document: Any) -> list[str]:
    """Return minimal structural and leak-risk errors for a report."""

    errors: list[str] = []
    if not isinstance(document, dict) or set(document) != {"schema_version", "feedback", "collection", "candidates"}:
        return ["Top-level report fields must be exactly schema_version, feedback, collection, and candidates"]
    feedback = document["feedback"]
    collection = document["collection"]
    candidates = document["candidates"]
    if document["schema_version"] != "0.1":
        errors.append("schema_version must be 0.1")
    if not isinstance(feedback, dict) or feedback.get("redaction_confirmed") is not True:
        errors.append("redaction_confirmed = true must be explicitly confirmed")
    if not isinstance(feedback, dict) or not re.fullmatch(r"[0-9a-f]{64}", feedback.get("source_fingerprint", "")):
        errors.append("An irreversible 64-character source_fingerprint is required")
    if not isinstance(collection, dict) or not collection.get("authorized_sources"):
        errors.append("At least one authorized_sources value is required")
    if not isinstance(candidates, list) or not candidates:
        errors.append("At least one candidate is required")
        return errors
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("scope") not in SCOPES:
            errors.append("Candidate scope must be local, project-plugin, or standard-candidate")
            continue
        if not candidate.get("evidence") or not isinstance(candidate["evidence"], list):
            errors.append(f"Candidate {candidate.get('id', '<unknown>')} lacks an evidence summary")
    for value in walk_strings(document):
        if FORBIDDEN.search(value):
            errors.append("Report may contain a path, URL, or credential; redact it and retry")
            break
    return errors


def walk_strings(value: Any):
    """Recursively enumerate string values in JSON."""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_feedback_report.py REPORT.json", file=sys.stderr)
        return 2
    try:
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to read report: {error}", file=sys.stderr)
        return 1
    errors = validate(document)
    if errors:
        print("Invalid feedback report: " + "; ".join(errors), file=sys.stderr)
        return 1
    print("Feedback report validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
