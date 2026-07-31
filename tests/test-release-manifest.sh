#!/bin/sh
set -eu

# 运行 Release 清单生成器单元测试；禁止测试过程产生 Python 缓存。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 "$script_dir/test-release-manifest.py"
