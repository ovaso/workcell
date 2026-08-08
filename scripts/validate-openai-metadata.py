#!/usr/bin/env python3
"""Validate basic interface fields in a Skill's agents/openai.yaml."""

from __future__ import annotations

import json
import pathlib
import re
import sys


def quoted_field(content: str, key: str) -> str:
    """Read a two-space-indented, double-quoted interface field."""

    match = re.search(rf'^  {re.escape(key)}: ("(?:[^"\\]|\\.)*")$', content, re.MULTILINE)
    if match is None:
        raise ValueError(f"missing or unquoted interface.{key}")
    return json.loads(match.group(1))


def main() -> int:
    """Check display name, short description, and default prompt against the Skill name."""

    if len(sys.argv) != 2:
        print("Usage: validate-openai-metadata.py <skill-directory>", file=sys.stderr)
        return 2
    skill_directory = pathlib.Path(sys.argv[1])
    metadata_path = skill_directory / "agents/openai.yaml"
    try:
        content = metadata_path.read_text(encoding="utf-8")
        if not content.startswith("interface:\n"):
            raise ValueError("metadata must start with interface")
        display_name = quoted_field(content, "display_name")
        short_description = quoted_field(content, "short_description")
        default_prompt = quoted_field(content, "default_prompt")
        if not display_name.strip():
            raise ValueError("display_name must not be empty")
        if not 25 <= len(short_description) <= 64:
            raise ValueError("short_description must contain 25-64 characters")
        if f"${skill_directory.name}" not in default_prompt:
            raise ValueError(f"default_prompt must mention ${skill_directory.name}")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Invalid agents/openai.yaml: {metadata_path}: {error}", file=sys.stderr)
        return 1
    print(f"VALID: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
