#!/bin/sh
set -eu

# 将发行物写到临时目录，避免污染仓库工作树。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
test_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-package-test.XXXXXX")

# 清理本次测试创建的临时发行物。
cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT HUP INT TERM

STD_WORKSPACE_DIST_DIR="$test_root" "$repo_root/scripts/package-bootstrap-skill.sh"

archive=$(find "$test_root" -maxdepth 1 -name 'bootstrap-standard-workspace-*.zip' -type f -print | head -n 1)
if [ -z "$archive" ] || [ ! -s "$archive" ] || [ ! -s "$archive.sha256" ]; then
  printf 'Package or checksum was not created.\n' >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$test_root" && sha256sum -c "$(basename "$archive").sha256" >/dev/null)
elif command -v shasum >/dev/null 2>&1; then
  (cd "$test_root" && shasum -a 256 -c "$(basename "$archive").sha256" >/dev/null)
fi

if command -v unzip >/dev/null 2>&1; then
  unzip -Z1 "$archive" | grep '^bootstrap-standard-workspace/SKILL.md$' >/dev/null
  unzip -Z1 "$archive" | grep '^bootstrap-standard-workspace/LICENSE$' >/dev/null
  unzip -Z1 "$archive" | grep '^bootstrap-standard-workspace/assets/workspace-v0.1/AI_WORKSPACE.md$' >/dev/null
fi
