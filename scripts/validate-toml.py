#!/usr/bin/env python3
"""Validate managed repository TOML files with the standard library."""

from __future__ import annotations

import pathlib
import sys
import tomllib


def repository_root() -> pathlib.Path:
    """Return the repository root that owns this script."""

    return pathlib.Path(__file__).resolve().parent.parent


def managed_toml_files(root: pathlib.Path) -> list[pathlib.Path]:
    """List TOML files in product source and distribution assets."""

    ignored_parts = {".git", "dist"}
    return sorted(
        path
        for path in root.rglob("*.toml")
        if not ignored_parts.intersection(path.parts)
    )


def main() -> int:
    """Parse all TOML and fail on the first syntax error."""

    root = repository_root()
    files = managed_toml_files(root)
    for path in files:
        try:
            with path.open("rb") as source:
                tomllib.load(source)
        except tomllib.TOMLDecodeError as error:
            print(f"Invalid TOML: {path.relative_to(root)}: {error}", file=sys.stderr)
            return 1
    print(f"Validated {len(files)} TOML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
