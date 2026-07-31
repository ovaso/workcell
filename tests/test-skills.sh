#!/bin/sh
set -eu

# 使用 Skill Creator 官方 quick_validate.py 检查外部与运行时 Skills。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-standard-workspace"
quick_validate=${STD_WORKSPACE_QUICK_VALIDATE:-"${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py"}

if [ ! -f "$quick_validate" ]; then
  printf 'Skill Creator quick_validate.py is unavailable: %s\n' "$quick_validate" >&2
  exit 1
fi

validate_one() {
  skill_path=$1
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo_root/tests/compat" \
    python3 "$quick_validate" "$skill_path"
  [ -s "$skill_path/agents/openai.yaml" ] || {
    printf 'Missing agents/openai.yaml: %s\n' "$skill_path" >&2
    exit 1
  }
  PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/validate-openai-metadata.py" "$skill_path" >/dev/null
}

validate_one "$skill_root"
validate_one "$repo_root/skills/integrate-workspace-feedback"
for skill_path in "$skill_root"/assets/workspace-v0.1/skills/*; do
  [ -d "$skill_path" ] || continue
  validate_one "$skill_path"
done

printf 'All Bootstrap and runtime Skills passed quick validation.\n'
