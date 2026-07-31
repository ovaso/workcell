#!/bin/sh
set -eu

# 输出统一的修复计划失败信息。
fail() {
    echo "ERROR: $*" >&2
    exit 2
}

# 校验 Manifest 路径，防止计划阶段逃逸工作区。
validate_manifest_path() {
    manifest_path=$1
    case "$manifest_path" in
        ""|\#*) return 1 ;;
        /*|.|..|./*|../*|*/./*|*/../*|*/.|*/..|*//*|*[[:space:]]*)
            fail "unsafe distribution manifest path: '$manifest_path'"
            ;;
    esac
    return 0
}

# 检查相对路径任一祖先或末端是否为符号链接，防止修复计划跟随外部路径。
path_contains_symlink_component() {
    link_root=$1
    link_remaining=$2
    link_current=$link_root

    while [ -n "$link_remaining" ]; do
        case "$link_remaining" in
            */*)
                link_component=${link_remaining%%/*}
                link_remaining=${link_remaining#*/}
                ;;
            *)
                link_component=$link_remaining
                link_remaining=
                ;;
        esac
        link_current=$link_current/$link_component
        if [ -L "$link_current" ]; then
            return 0
        fi
    done
    return 1
}

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <workspace-directory>" >&2
    exit 2
fi

script_directory=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
skill_directory=$(CDPATH='' cd "$script_directory/.." && pwd -P)
asset_directory=$skill_directory/assets/workspace-v0.1
workspace_input=$1

"$script_directory/validate-bundle.sh" >/dev/null

[ -d "$workspace_input" ] || fail "workspace directory does not exist: $workspace_input"
[ ! -L "$workspace_input" ] || fail "workspace directory must not be a symbolic link: $workspace_input"
workspace_directory=$(CDPATH='' cd "$workspace_input" && pwd -P)
"$script_directory/validate-workspace.sh" --metadata-only "$workspace_directory" >/dev/null
manifest_file=$asset_directory/.ai-workspace/distribution.manifest
[ -s "$manifest_file" ] || fail "bundle distribution manifest is missing: $manifest_file"

duplicate_path=$(awk '
    /^[[:space:]]*($|#)/ { next }
    seen[$0]++ { print; exit }
' "$manifest_file")
[ -z "$duplicate_path" ] || fail "duplicate distribution manifest path: $duplicate_path"

drift_found=false
while IFS= read -r managed_path || [ -n "$managed_path" ]; do
    case "$managed_path" in
        ""|\#*) continue ;;
    esac
    validate_manifest_path "$managed_path" || continue
    source_path=$asset_directory/$managed_path
    workspace_path=$workspace_directory/$managed_path
    repair_status=OK

    if path_contains_symlink_component "$asset_directory" "$managed_path" || path_contains_symlink_component "$workspace_directory" "$managed_path"; then
        repair_status=TYPE_MISMATCH
    elif [ -f "$source_path" ]; then
        if [ ! -e "$workspace_path" ]; then
            repair_status=MISSING
        elif [ ! -f "$workspace_path" ]; then
            repair_status=TYPE_MISMATCH
        elif ! cmp "$source_path" "$workspace_path" >/dev/null 2>&1; then
            repair_status=MODIFIED
        fi
    elif [ -d "$source_path" ]; then
        if [ ! -e "$workspace_path" ]; then
            repair_status=MISSING
        elif [ ! -d "$workspace_path" ]; then
            repair_status=TYPE_MISMATCH
        elif ! diff -r "$source_path" "$workspace_path" >/dev/null 2>&1; then
            repair_status=MODIFIED
        fi
    else
        repair_status=BUNDLE_MISSING
    fi

    printf '%s\t%s\n' "$repair_status" "$managed_path"
    if [ "$repair_status" != OK ]; then
        drift_found=true
    fi
done < "$manifest_file"

if [ "$drift_found" = true ]; then
    exit 1
fi
exit 0
