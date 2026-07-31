#!/bin/sh
set -eu

# 复用 Bootstrap Skill 自带的黑盒测试，验证真实分发目录。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

"$repo_root/skills/bootstrap-standard-workspace/tests/test-bootstrap.sh"
