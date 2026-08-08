#!/bin/sh
set -eu

# Map real TOML manifests to JSON and validate them with the same schemas.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-standard-workspace"
asset_root="$skill_root/assets/workspace-v0.1"
test_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-toml-schema.XXXXXX")

# Clean temporary JSON produced by conversion.
cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT HUP INT TERM

# Convert and validate one TOML/schema pair.
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
