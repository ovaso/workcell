#!/usr/bin/env python3
"""校验仓库内受管 TOML 文件能够被标准库解析。"""

from __future__ import annotations

import pathlib
import sys
import tomllib


def repository_root() -> pathlib.Path:
    """返回当前脚本所属的仓库根目录。"""

    return pathlib.Path(__file__).resolve().parent.parent


def managed_toml_files(root: pathlib.Path) -> list[pathlib.Path]:
    """列出产品源码和分发资产中的 TOML 文件。"""

    ignored_parts = {".git", "dist"}
    return sorted(
        path
        for path in root.rglob("*.toml")
        if not ignored_parts.intersection(path.parts)
    )


def main() -> int:
    """解析全部 TOML，并在首个语法错误处返回失败。"""

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
