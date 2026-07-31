#!/bin/sh
set -eu

# 获取仓库根目录，所有同步目标均由该绝对路径派生。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skill_root="$repo_root/skills/bootstrap-standard-workspace"
asset_root="$skill_root/assets/workspace-v0.1"
stage_root=$(mktemp -d "${TMPDIR:-/tmp}/std-workspace-build.XXXXXX")

# 清理本次构建使用的临时目录。
cleanup() {
  rm -rf "$stage_root"
}
trap cleanup EXIT HUP INT TERM

# 将一个源码目录原子同步到受控目标，防止旧文件残留。
replace_directory() {
  source_dir=$1
  target_dir=$2
  stage_dir="$stage_root/$(basename "$target_dir")-$$"

  case "$target_dir" in
    "$skill_root"/references/product-docs|\
    "$skill_root"/references/product-facts|\
    "$skill_root"/references/schemas|\
    "$skill_root"/references/specs|\
    "$skill_root"/LICENSES|\
    "$asset_root"/.ai-workspace/schemas|\
    "$asset_root"/.ai-workspace/specs|\
    "$asset_root"/docs/standard)
      ;;
    *)
      printf 'Refusing unsafe build target: %s\n' "$target_dir" >&2
      exit 1
      ;;
  esac

  mkdir -p "$stage_dir"
  cp -R "$source_dir"/. "$stage_dir"/
  rm -rf "$target_dir"
  mkdir -p "$(dirname "$target_dir")"
  mv "$stage_dir" "$target_dir"
}

# 计算文件 SHA-256；兼容常见 GNU 与 BSD/macOS 工具。
sha256_file() {
  file_path=$1
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file_path" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file_path" | awk '{print $1}'
  else
    printf 'Missing sha256sum or shasum\n' >&2
    exit 1
  fi
}

replace_directory "$repo_root/specs" "$skill_root/references/specs"
replace_directory "$repo_root/schemas" "$skill_root/references/schemas"

# 只把通用、发行安全的产品文档带入 Skill，排除会话溯源。
mkdir -p "$stage_root/release-product-docs"
for document in product-vision.md architecture.md lifecycle.md roadmap.md; do
  cp "$repo_root/docs/$document" "$stage_root/release-product-docs/$document"
done
replace_directory "$stage_root/release-product-docs" "$skill_root/references/product-docs"

# 只携带可复用决策和种子知识，来源工作区观察事实仅保留在源码仓库。
mkdir -p "$stage_root/release-product-facts"
for fact in known-tool-capabilities.toml session-decisions.toml; do
  cp "$repo_root/facts/$fact" "$stage_root/release-product-facts/$fact"
done
replace_directory "$stage_root/release-product-facts" "$skill_root/references/product-facts"

replace_directory "$repo_root/LICENSES" "$skill_root/LICENSES"
cp "$repo_root/LICENSE" "$skill_root/LICENSE"
replace_directory "$repo_root/specs" "$asset_root/.ai-workspace/specs"
replace_directory "$repo_root/schemas" "$asset_root/.ai-workspace/schemas"

# 将环境能力目录作为展开后工作区的发行种子知识，供事实刷新和建议流程读取。
mkdir -p "$asset_root/knowledge"
cp "$repo_root/facts/known-tool-capabilities.toml" "$asset_root/knowledge/tool-capabilities.toml"

mkdir -p "$stage_root/standard-docs"
for document in product-vision.md architecture.md lifecycle.md roadmap.md; do
  cp "$repo_root/docs/$document" "$stage_root/standard-docs/$document"
done
replace_directory "$stage_root/standard-docs" "$asset_root/docs/standard"

# 在外层 checksum 之前生成安装收据；该收据不自哈希，由外层清单保护。
release_version=$(tr -d '[:space:]' < "$repo_root/VERSION")
PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/generate-release-manifest.py" \
  --asset-root "$asset_root" \
  --release-version "$release_version"

mkdir -p "$skill_root/checksums"
checksum_file="$skill_root/checksums/workspace-v0.1.sha256"
: > "$checksum_file"
find "$asset_root" -type f -print | LC_ALL=C sort | while IFS= read -r file_path; do
  relative_path=${file_path#"$asset_root"/}
  digest=$(sha256_file "$file_path")
  printf '%s  %s\n' "$digest" "$relative_path" >> "$checksum_file"
done

printf 'Bootstrap assets synchronized for product %s\n' "$release_version"
