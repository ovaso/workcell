#!/bin/sh
set -eu

# Resolve deterministic repository and release-asset paths.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-workcell"
asset_root="$skill_root/assets/workspace-v0.1"
manifest="$asset_root/.ai-workspace/distribution.manifest"

# Assert that a repository-relative path exists.
require_path() {
  relative_path=$1
  if [ ! -e "$repo_root/$relative_path" ]; then
    printf 'Missing required path: %s\n' "$relative_path" >&2
    exit 1
  fi
}

# Require one canonical metadata line to prevent release-version drift.
require_exact_line() {
  expected_line=$1
  metadata_file=$2
  if ! grep -F -x "$expected_line" "$metadata_file" >/dev/null 2>&1; then
    printf 'Release version metadata mismatch in %s: expected %s\n' "$metadata_file" "$expected_line" >&2
    exit 1
  fi
}

for required_path in \
  README.md \
  LICENSE \
  CONTRIBUTING.md \
  CODE_OF_CONDUCT.md \
  SECURITY.md \
  SUPPORT.md \
  GOVERNANCE.md \
  VERSION \
  product.toml \
  .github/CODEOWNERS \
  .github/dependabot.yml \
  .github/workflows/ci.yml \
  .github/workflows/codeql.yml \
  .github/workflows/dependency-review.yml \
  .github/workflows/release-candidate.yml \
  schemas/release-manifest.schema.json \
  schemas/examples/release-manifest.example.json \
  schemas/workspace.schema.json \
  specs/workspace-spec-v0.1.md \
  scripts/build-bootstrap-assets.ps1 \
  scripts/package-bootstrap-skill.ps1 \
  scripts/validate-product.ps1 \
  skills/bootstrap-workcell/SKILL.md \
  skills/bootstrap-workcell/LICENSE \
  skills/bootstrap-workcell/scripts/create-workspace.ps1 \
  skills/bootstrap-workcell/scripts/plan-repair.ps1 \
  skills/bootstrap-workcell/scripts/validate-bundle.ps1 \
  skills/bootstrap-workcell/scripts/validate-workspace.ps1 \
  skills/bootstrap-workcell/assets/workspace-v0.1/AI_WORKSPACE.md \
  skills/bootstrap-workcell/assets/workspace-v0.1/AGENTS.md \
  skills/bootstrap-workcell/assets/workspace-v0.1/LICENSE \
  skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/release-manifest.json \
  skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/workspace.toml \
  skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/versions.lock \
  skills/bootstrap-workcell/assets/workspace-v0.1/knowledge/tool-capabilities.toml
do
  require_path "$required_path"
done

if [ ! -d "$repo_root/.git" ]; then
  printf 'workcell must be an independent Git repository.\n' >&2
  exit 1
fi

while IFS= read -r entry || [ -n "$entry" ]; do
  case "$entry" in
    ''|'#'*) continue ;;
  esac
  if [ ! -e "$asset_root/$entry" ]; then
    printf 'Distribution manifest points to missing path: %s\n' "$entry" >&2
    exit 1
  fi
done < "$manifest"

if find "$skill_root" -type l -print | grep . >/dev/null 2>&1; then
  printf 'Distributable Bootstrap Skill must not contain symbolic links.\n' >&2
  exit 1
fi

first_cache=$(find "$skill_root" \( \
  -name __pycache__ -o \
  -name '*.pyc' -o \
  -name '*.pyo' -o \
  -name .DS_Store -o \
  -name .pytest_cache -o \
  -name .mypy_cache -o \
  -name .ruff_cache \
\) -print | sed -n '1p')
if [ -n "$first_cache" ]; then
  printf 'Generated cache found in distributable Bootstrap Skill: %s\n' "$first_cache" >&2
  exit 1
fi

if rg -n --glob 'SKILL.md' '\bTODO\b|\[TODO' "$skill_root" >/dev/null 2>&1; then
  printf 'Skill placeholder found.\n' >&2
  rg -n --glob 'SKILL.md' '\bTODO\b|\[TODO' "$skill_root" >&2
  exit 1
fi

if rg -n '/Users/|/home/[^/]+/' "$skill_root" >/dev/null 2>&1 || \
  rg -n -F "\\Users\\" "$skill_root" >/dev/null 2>&1; then
  printf 'Host-specific absolute path found in distributable Bootstrap Skill.\n' >&2
  rg -n '/Users/|/home/[^/]+/' "$skill_root" >&2 || true
  rg -n -F "\\Users\\" "$skill_root" >&2 || true
  exit 1
fi

if rg -n -- '-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}' "$skill_root" >/dev/null 2>&1; then
  printf 'Credential-like material found in distributable Bootstrap Skill.\n' >&2
  exit 1
fi

node "$repo_root/scripts/validate-schema-examples.mjs"
python3 "$repo_root/scripts/validate-toml.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/validate-github-config.py"
release_version=$(tr -d '[:space:]' < "$repo_root/VERSION")
require_exact_line "version = \"$release_version\"" "$repo_root/product.toml"
require_exact_line "version = \"$release_version\"" "$skill_root/bundle.toml"
for version_metadata in \
  "$asset_root/.ai-workspace/workspace.toml" \
  "$asset_root/.ai-workspace/versions.lock" \
  "$asset_root/.ai-workspace/templates/workspace.toml" \
  "$asset_root/.ai-workspace/templates/versions.lock"
do
  require_exact_line "product = \"$release_version\"" "$version_metadata"
done
PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/generate-release-manifest.py" \
  --asset-root "$asset_root" \
  --release-version "$release_version" \
  --check
node "$repo_root/scripts/validate-json-instance.mjs" \
  "$repo_root/schemas/release-manifest.schema.json" \
  "$asset_root/.ai-workspace/release-manifest.json" >/dev/null

runtime_skill_count=$(find "$asset_root/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d '[:space:]')
if [ "$runtime_skill_count" -ne 9 ]; then
  printf 'Expected 9 runtime skills, found %s.\n' "$runtime_skill_count" >&2
  exit 1
fi

printf 'Product structure validation passed.\n'
