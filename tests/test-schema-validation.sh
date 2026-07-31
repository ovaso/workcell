#!/bin/sh
set -eu

# 解析并验证全部 Schema 示例以及受管 TOML。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

node "$repo_root/scripts/validate-schema-examples.mjs"
node "$repo_root/tests/test-schema-validator.mjs"
python3 "$repo_root/scripts/validate-toml.py"
"$repo_root/tests/test-toml-schema-mapping.sh"
"$repo_root/tests/test-runtime-contracts.sh"
