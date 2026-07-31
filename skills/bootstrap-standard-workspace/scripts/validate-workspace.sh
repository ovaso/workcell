#!/bin/sh
set -eu

# 输出统一的工作区校验失败信息。
fail() {
    echo "ERROR: $*" >&2
    exit 2
}

# 输出可修复的发行版漂移，并使用约定的漂移退出码。
drift() {
    echo "DRIFT: $*" >&2
    exit 1
}

# 按工作区 V0.1 的受限 TOML 子集校验 section、键、类型和重复定义。
validate_metadata_toml() {
    metadata_file=$1
    metadata_profile=$2
    if ! awk -v profile="$metadata_profile" '
        function trim(value) {
            sub(/^[[:space:]]+/, "", value)
            sub(/[[:space:]]+$/, "", value)
            return value
        }
        function strip_comment(value, result, position, character, quoted, escaped) {
            result = ""
            quoted = 0
            escaped = 0
            for (position = 1; position <= length(value); position++) {
                character = substr(value, position, 1)
                if (quoted) {
                    result = result character
                    if (escaped) {
                        escaped = 0
                    } else if (character == "\\") {
                        escaped = 1
                    } else if (character == "\"") {
                        quoted = 0
                    }
                } else if (character == "#") {
                    break
                } else {
                    result = result character
                    if (character == "\"") {
                        quoted = 1
                    }
                }
            }
            return result
        }
        function valid_string(value, inner) {
            if (length(value) < 2 || substr(value, 1, 1) != "\"" || substr(value, length(value), 1) != "\"") {
                return 0
            }
            inner = substr(value, 2, length(value) - 2)
            return inner !~ /["\\]/
        }
        function add_type(section_name, key_name, value_type) {
            declared_type[section_name "." key_name] = value_type
            allowed_section[section_name] = 1
        }
        BEGIN {
            if (profile == "workspace") {
                add_type("workspace", "id", "string")
                add_type("workspace", "name", "string")
                add_type("workspace", "status", "string")
                add_type("workspace", "managed_by", "string")
                add_type("workspace", "created_at", "string")
                add_type("workspace", "updated_at", "string")
                add_type("versions", "product", "string")
                add_type("versions", "workspace_schema", "string")
                add_type("versions", "release_manifest_schema", "string")
                add_type("versions", "environment_facts_schema", "string")
                add_type("versions", "project_plugin_schema", "string")
                add_type("versions", "diagnostic_profile_schema", "string")
                add_type("versions", "task_schema", "string")
                add_type("versions", "feedback_report_schema", "string")
                allowed_section["paths"] = 1
                add_type("safety", "remote_operations_default", "string")
                add_type("safety", "bootstrap_network", "string")
                add_type("safety", "overwrite_non_empty", "boolean")
            } else if (profile == "versions") {
                add_type("versions", "product", "string")
                add_type("versions", "workspace_schema", "string")
                add_type("versions", "release_manifest_schema", "string")
                add_type("versions", "environment_facts_schema", "string")
                add_type("versions", "project_plugin_schema", "string")
                add_type("versions", "diagnostic_profile_schema", "string")
                add_type("versions", "task_schema", "string")
                add_type("versions", "feedback_report_schema", "string")
                add_type("versions", "project_plugin_api", "string")
                add_type("versions", "diagnostic_plugin_api", "string")
                add_type("release", "channel", "string")
                add_type("release", "source", "string")
                add_type("release", "self_update", "boolean")
            } else {
                invalid = 1
            }
        }
        {
            line = trim(strip_comment($0))
            if (line == "") {
                next
            }
            if (line ~ /^\[/) {
                if (line !~ /^\[[a-z0-9_.-]+\]$/) {
                    invalid = 1
                    next
                }
                section = substr(line, 2, length(line) - 2)
                if (!allowed_section[section] || seen_section[section]++) {
                    invalid = 1
                }
                next
            }

            separator = index(line, "=")
            if (separator == 0 || section == "") {
                invalid = 1
                next
            }
            key = trim(substr(line, 1, separator - 1))
            value = trim(substr(line, separator + 1))
            qualified_key = section "." key
            value_type = declared_type[qualified_key]
            if (profile == "workspace" && section == "paths" && key ~ /^[a-z0-9_.-]+$/) {
                value_type = "string"
            }
            if (value_type == "" || seen_key[qualified_key]++) {
                invalid = 1
            } else if (value_type == "string" && !valid_string(value)) {
                invalid = 1
            } else if (value_type == "boolean" && value != "true" && value != "false") {
                invalid = 1
            }
        }
        END { exit invalid }
    ' "$metadata_file"; then
        fail "invalid or non-canonical TOML metadata: $metadata_file"
    fi
}

# 从简单 TOML 表中读取字符串值；V0.1 元数据禁止多行值和重复键。
toml_value() {
    toml_file=$1
    toml_section=$2
    toml_key=$3
    awk -v wanted_section="$toml_section" -v wanted_key="$toml_key" '
        function trim(value) {
            sub(/^[[:space:]]+/, "", value)
            sub(/[[:space:]]+$/, "", value)
            return value
        }
        {
            line = $0
            sub(/[[:space:]]*#.*/, "", line)
            line = trim(line)
            if (line == "[" wanted_section "]") {
                in_section = 1
                next
            }
            if (line ~ /^\[/) {
                in_section = 0
            }
            if (in_section && line ~ ("^" wanted_key "[[:space:]]*=")) {
                sub(/^[^=]*=[[:space:]]*/, "", line)
                line = trim(line)
                if (line ~ /^".*"$/) {
                    sub(/^"/, "", line)
                    sub(/"$/, "", line)
                }
                found_count++
                found_value = line
            }
        }
        END {
            if (found_count > 1) {
                exit 2
            }
            if (found_count == 1) {
                print found_value
            }
        }
    ' "$toml_file"
}

# 校验必需 TOML 字段存在且与当前 Bundle 兼容。
require_toml_value() {
    value_file=$1
    value_section=$2
    value_key=$3
    expected_value=$4
    actual_value=$(toml_value "$value_file" "$value_section" "$value_key") || fail "$value_file contains duplicate [$value_section].$value_key keys"
    if [ "$actual_value" != "$expected_value" ]; then
        fail "$value_file [$value_section].$value_key expected '$expected_value', got '${actual_value:-<missing>}'"
    fi
}

# 校验 Manifest 路径是规范化的工作区内相对路径。
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

# 检查相对路径任一祖先或末端是否为符号链接，避免越出工作区根目录。
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

# 比较当前版本中受发行版管理的文件和目录。
validate_distribution_files() {
    manifest_file=$asset_directory/.ai-workspace/distribution.manifest
    workspace_manifest=$workspace_directory/.ai-workspace/distribution.manifest
    [ -s "$manifest_file" ] || fail "bundle distribution manifest is missing"
    [ -s "$workspace_manifest" ] || drift "workspace distribution manifest is missing"
    cmp "$manifest_file" "$workspace_manifest" >/dev/null 2>&1 || drift "workspace distribution manifest differs from the bundle"
    duplicate_path=$(awk '
        /^[[:space:]]*($|#)/ { next }
        seen[$0]++ { print; exit }
    ' "$manifest_file")
    [ -z "$duplicate_path" ] || fail "duplicate distribution manifest path: $duplicate_path"

    while IFS= read -r managed_path || [ -n "$managed_path" ]; do
        case "$managed_path" in
            ""|\#*) continue ;;
        esac
        validate_manifest_path "$managed_path" || continue
        source_path=$asset_directory/$managed_path
        workspace_path=$workspace_directory/$managed_path

        if path_contains_symlink_component "$asset_directory" "$managed_path" || path_contains_symlink_component "$workspace_directory" "$managed_path"; then
            drift "symbolic link found in distribution path: $managed_path"
        fi
        if [ -f "$source_path" ]; then
            [ -f "$workspace_path" ] || drift "missing distribution file: $managed_path"
            cmp "$source_path" "$workspace_path" >/dev/null 2>&1 || drift "modified distribution file: $managed_path"
        elif [ -d "$source_path" ]; then
            [ -d "$workspace_path" ] || drift "missing distribution directory: $managed_path"
            diff -r "$source_path" "$workspace_path" >/dev/null 2>&1 || drift "modified distribution directory: $managed_path"
        else
            fail "distribution manifest references missing bundle path: $managed_path"
        fi
    done < "$manifest_file"
}

metadata_only=false
if [ "$#" -eq 1 ]; then
    workspace_input=$1
elif [ "$#" -eq 2 ] && [ "$1" = "--metadata-only" ]; then
    metadata_only=true
    workspace_input=$2
else
    echo "Usage: $0 [--metadata-only] <workspace-directory>" >&2
    exit 2
fi

script_directory=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
skill_directory=$(CDPATH='' cd "$script_directory/.." && pwd -P)
asset_directory=$skill_directory/assets/workspace-v0.1

[ -d "$workspace_input" ] || fail "workspace directory does not exist: $workspace_input"
[ ! -L "$workspace_input" ] || fail "workspace directory must not be a symbolic link: $workspace_input"
workspace_directory=$(CDPATH='' cd "$workspace_input" && pwd -P)

[ ! -L "$workspace_directory/.ai-workspace" ] || fail "required directory must not be a symbolic link: .ai-workspace"
[ -d "$workspace_directory/.ai-workspace" ] || fail "missing required directory: .ai-workspace"

if [ "$metadata_only" = false ]; then
    for required_directory in \
        skills \
        environment \
        project \
        mirror \
        remotes \
        requirements \
        workspaces \
        diagnostics \
        tools \
        knowledge \
        docs \
        memory
    do
        [ ! -L "$workspace_directory/$required_directory" ] || fail "required directory must not be a symbolic link: $required_directory"
        [ -d "$workspace_directory/$required_directory" ] || fail "missing required directory: $required_directory"
    done
fi

if [ "$metadata_only" = false ]; then
    for distribution_entry_file in \
        AI_WORKSPACE.md \
        .ai-workspace/release-manifest.json \
        .ai-workspace/distribution.manifest
    do
        path_contains_symlink_component "$workspace_directory" "$distribution_entry_file" && drift "symbolic link found in distribution entry: $distribution_entry_file"
        [ -s "$workspace_directory/$distribution_entry_file" ] || drift "missing distribution entry file: $distribution_entry_file"
    done
fi

for required_workspace_file in \
    .ai-workspace/workspace.toml \
    .ai-workspace/versions.lock
do
    path_contains_symlink_component "$workspace_directory" "$required_workspace_file" && fail "symbolic link found in required workspace file: $required_workspace_file"
    [ -s "$workspace_directory/$required_workspace_file" ] || fail "missing required workspace file: $required_workspace_file"
done

if [ "$metadata_only" = false ]; then
    path_contains_symlink_component "$workspace_directory" AGENTS.md && fail "symbolic link found in required workspace file: AGENTS.md"
    [ -s "$workspace_directory/AGENTS.md" ] || fail "missing required workspace file: AGENTS.md"
fi

workspace_file=$workspace_directory/.ai-workspace/workspace.toml
versions_file=$workspace_directory/.ai-workspace/versions.lock

validate_metadata_toml "$workspace_file" workspace
validate_metadata_toml "$versions_file" versions

workspace_id=$(toml_value "$workspace_file" workspace id) || fail "workspace id is duplicated"
workspace_name=$(toml_value "$workspace_file" workspace name) || fail "workspace name is duplicated"
workspace_status=$(toml_value "$workspace_file" workspace status) || fail "workspace status is duplicated"
workspace_manager=$(toml_value "$workspace_file" workspace managed_by) || fail "workspace managed_by is duplicated"
[ -n "$workspace_id" ] || fail "workspace id is missing"
[ -n "$workspace_name" ] || fail "workspace name is missing"
[ "$workspace_manager" = "ai-native-standard-workspace" ] || fail "workspace managed_by is invalid"
printf '%s\n' "$workspace_id" | grep -E '^[a-z0-9][a-z0-9._-]{1,63}$' >/dev/null 2>&1 || fail "workspace id is invalid: $workspace_id"

case "$workspace_status" in
    CREATED|ENVIRONMENT_INITIALIZED|PROJECT_ATTACHED|PROJECT_ADAPTED|DIAGNOSTICS_CONFIGURED|READY|DEGRADED|PAUSED|ARCHIVED) ;;
    *) fail "unsupported workspace status: '${workspace_status:-<missing>}'" ;;
esac

for version_pair in \
    'product:0.1.0' \
    'workspace_schema:0.1' \
    'release_manifest_schema:0.1' \
    'environment_facts_schema:0.1' \
    'project_plugin_schema:0.1' \
    'diagnostic_profile_schema:0.1' \
    'task_schema:0.1' \
    'feedback_report_schema:0.1'
do
    version_key=${version_pair%%:*}
    expected_version=${version_pair#*:}
    require_toml_value "$workspace_file" versions "$version_key" "$expected_version"
    require_toml_value "$versions_file" versions "$version_key" "$expected_version"
done

for path_pair in \
    'environment:environment' \
    'project:project' \
    'requirements:requirements' \
    'workspaces:workspaces' \
    'skills:skills' \
    'feedback:feedback'
do
    path_key=${path_pair%%:*}
    expected_path=${path_pair#*:}
    require_toml_value "$workspace_file" paths "$path_key" "$expected_path"
done

require_toml_value "$workspace_file" safety remote_operations_default deny
require_toml_value "$workspace_file" safety bootstrap_network deny
require_toml_value "$workspace_file" safety overwrite_non_empty false

require_toml_value "$versions_file" versions project_plugin_api 0.1
require_toml_value "$versions_file" versions diagnostic_plugin_api 0.1
require_toml_value "$versions_file" release self_update false

if [ "$metadata_only" = true ]; then
    echo "VALID: workspace metadata $workspace_directory"
    exit 0
fi

validate_distribution_files
echo "VALID: workspace $workspace_directory"
