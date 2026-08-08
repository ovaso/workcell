#!/usr/bin/env python3
"""Convert one TOML document to JSON for schema validation."""

from __future__ import annotations

import json
import pathlib
import sys
import tomllib


def main() -> int:
    """Read the single input path and write the parsed result to standard output."""

    if len(sys.argv) != 2:
        print("Usage: toml-to-json.py <document.toml>", file=sys.stderr)
        return 2
    source_path = pathlib.Path(sys.argv[1])
    with source_path.open("rb") as source:
        document = tomllib.load(source)
    json.dump(document, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
