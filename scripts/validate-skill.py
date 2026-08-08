#!/usr/bin/env python3
"""Validate the portable subset of Codex Skill frontmatter used by this repo."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(skill_file: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {}, [f"cannot read UTF-8 SKILL.md: {exc}"]

    text = text.replace("\r\n", "\n")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    if match is None:
        return {}, ["SKILL.md must begin with YAML frontmatter delimited by ---"]

    values: dict[str, str] = {}
    for line_number, line in enumerate(match.group(1).splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            errors.append(
                f"line {line_number}: use one top-level 'key: value' entry per line"
            )
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in values:
            errors.append(f"line {line_number}: duplicate frontmatter key: {key}")
            continue
        if key not in ALLOWED_KEYS:
            errors.append(f"line {line_number}: unsupported frontmatter key: {key}")
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value

    return values, errors


def validate_skill(skill_path: Path) -> list[str]:
    skill_file = skill_path / "SKILL.md" if skill_path.is_dir() else skill_path
    if not skill_file.is_file():
        return [f"missing SKILL.md: {skill_file}"]

    values, errors = parse_frontmatter(skill_file)
    name = values.get("name")
    description = values.get("description")

    if not name:
        errors.append("frontmatter field 'name' is required")
    elif len(name) > 64:
        errors.append("frontmatter field 'name' must be at most 64 characters")
    elif NAME_PATTERN.fullmatch(name) is None:
        errors.append("frontmatter field 'name' must use lowercase hyphen-case")

    if not description:
        errors.append("frontmatter field 'description' is required")
    elif len(description) > 1024:
        errors.append("frontmatter field 'description' must be at most 1024 characters")
    elif "<" in description or ">" in description:
        errors.append("frontmatter field 'description' must not contain angle brackets")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", type=Path, help="Skill directory or SKILL.md path")
    args = parser.parse_args()

    errors = validate_skill(args.skill.resolve())
    if errors:
        for error in errors:
            print(f"Skill validation error: {error}", file=sys.stderr)
        return 1

    print(f"Skill validation passed: {args.skill}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
