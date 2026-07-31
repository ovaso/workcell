#!/bin/sh
set -eu

# 获取仓库、版本与发行目录。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
version=$(tr -d '[:space:]' < "$repo_root/VERSION")
skill_name="bootstrap-standard-workspace"
dist_dir=${STD_WORKSPACE_DIST_DIR:-"$repo_root/dist"}
archive="$dist_dir/$skill_name-$version.zip"

if ! command -v zip >/dev/null 2>&1; then
  printf 'zip command is required to create the release artifact.\n' >&2
  exit 1
fi

"$repo_root/scripts/build-bootstrap-assets.sh"
"$repo_root/scripts/validate-product.sh"

mkdir -p "$dist_dir"
rm -f "$archive" "$archive.sha256"
(
  cd "$repo_root/skills"
  zip -q -r "$archive" "$skill_name"
)

if command -v sha256sum >/dev/null 2>&1; then
  (
    cd "$dist_dir"
    sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256"
  )
elif command -v shasum >/dev/null 2>&1; then
  (
    cd "$dist_dir"
    shasum -a 256 "$(basename "$archive")" > "$(basename "$archive").sha256"
  )
else
  printf 'Missing sha256sum or shasum\n' >&2
  exit 1
fi

printf 'Created %s\n' "$archive"
