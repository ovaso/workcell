#!/bin/sh
set -eu

# Check every outer and runtime Skill with the repository validator. Run Skill
# Creator's official validator too when it is available on the host.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-workcell"
quick_validate=${WORKCELL_QUICK_VALIDATE:-"${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py"}
require_official=${WORKCELL_REQUIRE_OFFICIAL_SKILL_VALIDATOR:-0}

if [ -n "${WORKCELL_QUICK_VALIDATE:-}" ] && [ ! -f "$quick_validate" ]; then
  printf 'Skill Creator quick_validate.py is unavailable: %s\n' "$quick_validate" >&2
  exit 1
fi
if [ "$require_official" = 1 ] && [ ! -f "$quick_validate" ]; then
  printf 'Skill Creator quick_validate.py is required but unavailable: %s\n' "$quick_validate" >&2
  exit 1
fi

validate_one() {
  skill_path=$1
  PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/validate-skill.py" "$skill_path" >/dev/null
  if [ -f "$quick_validate" ]; then
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo_root/tests/compat" \
      python3 "$quick_validate" "$skill_path" >/dev/null
  fi
  [ -s "$skill_path/agents/openai.yaml" ] || {
    printf 'Missing agents/openai.yaml: %s\n' "$skill_path" >&2
    exit 1
  }
  PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/validate-openai-metadata.py" "$skill_path" >/dev/null
}

validate_one "$skill_root"
validate_one "$repo_root/skills/integrate-workcell-feedback"
for skill_path in "$skill_root"/assets/workspace-v0.1/skills/*; do
  [ -d "$skill_path" ] || continue
  validate_one "$skill_path"
done

if [ -f "$quick_validate" ]; then
  printf 'All Bootstrap and runtime Skills passed repository and official quick validation.\n'
else
  printf 'All Bootstrap and runtime Skills passed self-contained repository validation.\n'
fi
