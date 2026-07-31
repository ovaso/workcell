#!/bin/sh
set -eu

# 在构建前后验证源码真相与分发副本一致，防止测试先改写再掩盖漂移。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-standard-workspace"
asset_root="$skill_root/assets/workspace-v0.1"
test_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-build-sync.XXXXXX")

# 清理本次确定性构建测试的隔离快照。
cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT HUP INT TERM

# 断言目录只包含给定的相对普通文件集合。
assert_exact_files() {
  checked_directory=$1
  shift
  actual_files=$(cd "$checked_directory" && find . -type f -print | sed 's#^\./##' | LC_ALL=C sort)
  expected_files=$(printf '%s\n' "$@" | LC_ALL=C sort)
  if [ "$actual_files" != "$expected_files" ]; then
    printf 'Unexpected generated file set in %s\n' "$checked_directory" >&2
    printf 'Expected:\n%s\nActual:\n%s\n' "$expected_files" "$actual_files" >&2
    exit 1
  fi
}

# 执行只读同步断言；任何旧副本、额外溯源文件或 checksum 漂移都必须失败。
assert_generated_assets() {
  diff -qr "$repo_root/specs" "$skill_root/references/specs"
  diff -qr "$repo_root/schemas" "$skill_root/references/schemas"
  assert_exact_files "$skill_root/references/product-docs" \
    architecture.md \
    lifecycle.md \
    product-vision.md \
    roadmap.md
  for document in architecture.md lifecycle.md product-vision.md roadmap.md; do
    cmp "$repo_root/docs/$document" "$skill_root/references/product-docs/$document"
    cmp "$repo_root/docs/$document" "$asset_root/docs/standard/$document"
  done
  assert_exact_files "$skill_root/references/product-facts" \
    known-tool-capabilities.toml \
    session-decisions.toml
  for fact in known-tool-capabilities.toml session-decisions.toml; do
    cmp "$repo_root/facts/$fact" "$skill_root/references/product-facts/$fact"
  done
  diff -qr "$repo_root/LICENSES" "$skill_root/LICENSES"
  cmp "$repo_root/LICENSE" "$skill_root/LICENSE"
  diff -qr "$repo_root/specs" "$asset_root/.ai-workspace/specs"
  diff -qr "$repo_root/schemas" "$asset_root/.ai-workspace/schemas"
  cmp "$repo_root/facts/known-tool-capabilities.toml" "$asset_root/knowledge/tool-capabilities.toml"

  release_version=$(tr -d '[:space:]' < "$repo_root/VERSION")
  PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/generate-release-manifest.py" \
    --asset-root "$asset_root" \
    --release-version "$release_version" \
    --check
  node "$repo_root/scripts/validate-json-instance.mjs" \
    "$repo_root/schemas/release-manifest.schema.json" \
    "$asset_root/.ai-workspace/release-manifest.json" >/dev/null

  [ -s "$skill_root/checksums/workspace-v0.1.sha256" ] || {
    printf 'Workspace checksum manifest was not generated.\n' >&2
    exit 1
  }
  "$skill_root/scripts/validate-bundle.sh" >/dev/null
}

# 先检查当前仓库，确保测试不会用构建步骤掩盖待提交漂移。
assert_generated_assets
cp "$asset_root/.ai-workspace/release-manifest.json" "$test_root/release-manifest.json"
cp "$skill_root/checksums/workspace-v0.1.sha256" "$test_root/workspace-v0.1.sha256"

# 再验证构建幂等，生成收据和外层 checksum 的字节必须稳定。
"$repo_root/scripts/build-bootstrap-assets.sh"
cmp "$test_root/release-manifest.json" "$asset_root/.ai-workspace/release-manifest.json"
cmp "$test_root/workspace-v0.1.sha256" "$skill_root/checksums/workspace-v0.1.sha256"
assert_generated_assets
