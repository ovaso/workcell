#!/bin/sh
set -eu

# 验证确定性运行时工具的实际输出符合仓库级 Schema。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
asset_root="$repo_root/skills/bootstrap-standard-workspace/assets/workspace-v0.1"
test_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-runtime-contracts.XXXXXX")

# 清理运行时契约测试输出。
cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT HUP INT TERM

environment_json="$test_root/environment.json"
node "$repo_root/scripts/validate-json-instance.mjs" \
  "$repo_root/schemas/environment-facts.schema.json" \
  "$asset_root/environment/current/host-facts.json" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$asset_root/skills/inspect-host-environment/scripts/inspect_host.py" \
  --context ai-execution \
  --no-default-commands \
  --skip-environment-names \
  --output "$environment_json"

node "$repo_root/scripts/validate-json-instance.mjs" \
  "$repo_root/schemas/environment-facts.schema.json" \
  "$environment_json" >/dev/null

project_json="$test_root/project-plugin.json"
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$asset_root/skills/adapt-project-workspace/scripts/build_project_plugin.py" \
  --input "$asset_root/.ai-workspace/templates/project-plugin.json" \
  --output "$project_json"

node "$repo_root/scripts/validate-json-instance.mjs" \
  "$repo_root/schemas/project-plugin.schema.json" \
  "$project_json" >/dev/null

printf 'Runtime environment and project contracts passed.\n'
