#!/bin/sh
set -eu

# 将真实 TOML Manifest 映射为 JSON 后，使用同一组 Schema 校验。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-standard-workspace"
asset_root="$skill_root/assets/workspace-v0.1"
test_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-toml-schema.XXXXXX")

# 清理转换过程中产生的临时 JSON。
cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT HUP INT TERM

# 转换并校验一个 TOML 与 Schema 对。
validate_toml_instance() {
  schema_name=$1
  toml_path=$2
  json_path="$test_root/$schema_name.json"
  python3 "$repo_root/scripts/toml-to-json.py" "$toml_path" > "$json_path"
  node "$repo_root/scripts/validate-json-instance.mjs" "$repo_root/schemas/$schema_name.schema.json" "$json_path" >/dev/null
}

validate_toml_instance bundle "$skill_root/bundle.toml"
validate_toml_instance workspace "$asset_root/.ai-workspace/workspace.toml"
validate_toml_instance diagnostic-profile "$asset_root/project/diagnostics/diagnostic-profile.toml"
validate_toml_instance task "$asset_root/.ai-workspace/templates/task.toml"

printf 'Validated TOML-to-Schema mappings.\n'
