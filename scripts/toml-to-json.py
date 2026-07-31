#!/usr/bin/env python3
"""将一个 TOML 文档转换为供 Schema 校验使用的 JSON。"""

from __future__ import annotations

import json
import pathlib
import sys
import tomllib


def main() -> int:
    """读取唯一输入路径并把解析结果写到标准输出。"""

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
