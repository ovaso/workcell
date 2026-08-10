#!/bin/sh
set -eu

# Print a consistent bundle-validation failure.
fail() {
    echo "ERROR: $*" >&2
    exit 2
}

# Verify that an exact required metadata line exists.
require_exact_line() {
    expected_line=$1
    metadata_file=$2
    if ! grep -F -x "$expected_line" "$metadata_file" >/dev/null 2>&1; then
        fail "missing required metadata '$expected_line' in $metadata_file"
    fi
}

# Validate bundle structure, types, duplicates, and entry points against the constrained V0.1 TOML contract.
validate_bundle_metadata() {
    if ! awk '
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
        function reject(message) {
            print message > "/dev/stderr"
            invalid = 1
        }
        BEGIN {
            allowed_section["bundle"] = 1
            allowed_section["versions"] = 1
            allowed_section["payload"] = 1
            allowed_section["safety"] = 1

            type["bundle.id"] = "string"
            type["bundle.version"] = "string"
            type["bundle.status"] = "string"
            type["bundle.format"] = "string"
            type["versions.workspace"] = "string"
            type["versions.release_manifest"] = "string"
            type["versions.environment_facts"] = "string"
            type["versions.project_plugin"] = "string"
            type["versions.diagnostic_profile"] = "string"
            type["versions.task"] = "string"
            type["versions.feedback_report"] = "string"
            type["versions.project_plugin_api"] = "string"
            type["versions.diagnostic_plugin_api"] = "string"
            type["payload.workspace_asset"] = "string"
            type["payload.required_entries"] = "array"
            type["safety.network_default"] = "string"
            type["safety.install_tools"] = "boolean"
            type["safety.modify_shell"] = "boolean"
            type["safety.overwrite_non_empty"] = "boolean"
            type["safety.self_update"] = "boolean"

            expected_entry["AI_WORKSPACE.md"] = 1
            expected_entry["AGENTS.md"] = 1
            expected_entry["LICENSE"] = 1
            expected_entry[".ai-workspace/workspace.toml"] = 1
            expected_entry[".ai-workspace/versions.lock"] = 1
            expected_entry[".ai-workspace/release-manifest.json"] = 1
            expected_entry[".ai-workspace/distribution.manifest"] = 1
            expected_entry[".ai-workspace/ownership.toml"] = 1
            expected_entry["skills"] = 1
        }
        {
            line = trim(strip_comment($0))
            if (line == "") {
                next
            }

            if (in_array) {
                if (line == "]") {
                    in_array = 0
                    next
                }
                array_value = line
                sub(/,$/, "", array_value)
                array_value = trim(array_value)
                if (!valid_string(array_value)) {
                    reject("invalid required_entries item at line " NR)
                    next
                }
                array_value = substr(array_value, 2, length(array_value) - 2)
                if (array_value == "" || seen_entry[array_value]++) {
                    reject("empty or duplicate required_entries item at line " NR)
                }
                entry_count++
                next
            }

            if (line ~ /^\[/) {
                if (line !~ /^\[[a-z_]+\]$/) {
                    reject("invalid Bundle section at line " NR)
                    next
                }
                section = substr(line, 2, length(line) - 2)
                if (!allowed_section[section] || seen_section[section]++) {
                    reject("unknown or duplicate Bundle section at line " NR)
                }
                next
            }

            separator = index(line, "=")
            if (separator == 0 || section == "") {
                reject("invalid Bundle assignment at line " NR)
                next
            }
            key = trim(substr(line, 1, separator - 1))
            value = trim(substr(line, separator + 1))
            qualified_key = section "." key
            if (!(qualified_key in type) || seen_key[qualified_key]++) {
                reject("unknown or duplicate Bundle key at line " NR)
                next
            }

            if (type[qualified_key] == "string" && !valid_string(value)) {
                reject("Bundle string type mismatch at line " NR)
            } else if (type[qualified_key] == "boolean" && value != "true" && value != "false") {
                reject("Bundle boolean type mismatch at line " NR)
            } else if (type[qualified_key] == "array") {
                if (value != "[") {
                    reject("Bundle array must use canonical multiline form at line " NR)
                } else {
                    in_array = 1
                }
            }
        }
        END {
            if (in_array || entry_count == 0) {
                invalid = 1
            }
            for (required_key in type) {
                if (seen_key[required_key] != 1) {
                    invalid = 1
                }
            }
            for (required_entry in expected_entry) {
                if (!seen_entry[required_entry]) {
                    invalid = 1
                }
            }
            exit invalid
        }
    ' "$bundle_file"; then
        fail "bundle.toml violates the canonical V0.1 metadata contract"
    fi
}

# Verify that each runtime Skill directory matches its YAML name.
validate_runtime_skill() {
    runtime_name=$1
    runtime_file=$asset_directory/skills/$runtime_name/SKILL.md
    runtime_agent_file=$asset_directory/skills/$runtime_name/agents/openai.yaml
    [ -s "$runtime_file" ] || fail "missing runtime Skill: $runtime_file"
    [ -s "$runtime_agent_file" ] || fail "missing runtime Skill agent metadata: $runtime_agent_file"
    first_line=$(sed -n '1p' "$runtime_file")
    [ "$first_line" = "---" ] || fail "invalid Skill frontmatter start: $runtime_file"
    if ! grep -F -x "name: $runtime_name" "$runtime_file" >/dev/null 2>&1; then
        fail "runtime Skill name does not match directory: $runtime_file"
    fi
    grep -E '^description: .+' "$runtime_file" >/dev/null 2>&1 || fail "runtime Skill description is missing: $runtime_file"
    placeholder_marker=TO"DO"
    if grep -F "$placeholder_marker" "$runtime_file" >/dev/null 2>&1; then
        fail "runtime Skill contains an unresolved template placeholder: $runtime_file"
    fi
}

# Verify that ownership.toml explicitly classifies every repair-manifest path as distribution.
validate_manifest_ownership() {
    ownership_file=$asset_directory/.ai-workspace/ownership.toml
    manifest_file=$asset_directory/.ai-workspace/distribution.manifest
    [ -s "$ownership_file" ] || fail "missing ownership policy: $ownership_file"
    [ -s "$manifest_file" ] || fail "missing distribution manifest: $manifest_file"

    if ! awk '
        function trim(value) {
            sub(/^[[:space:]]+/, "", value)
            sub(/[[:space:]]+$/, "", value)
            return value
        }
        function unquote(value) {
            value = trim(value)
            sub(/^"/, "", value)
            sub(/"$/, "", value)
            return value
        }
        FNR == NR {
            line = $0
            sub(/[[:space:]]*#.*/, "", line)
            line = trim(line)
            if (line ~ /^default[[:space:]]*=/) {
                value = line
                sub(/^[^=]*=/, "", value)
                default_owner = unquote(value)
            } else if (line ~ /^resolution[[:space:]]*=/) {
                value = line
                sub(/^[^=]*=/, "", value)
                resolution = unquote(value)
            } else if (line ~ /^pattern[[:space:]]*=/) {
                value = line
                sub(/^[^=]*=/, "", value)
                pending_pattern = unquote(value)
            } else if (line ~ /^owner[[:space:]]*=/ && pending_pattern != "") {
                value = line
                sub(/^[^=]*=/, "", value)
                rule_count++
                rule_pattern[rule_count] = pending_pattern
                rule_owner[rule_count] = unquote(value)
                pending_pattern = ""
            }
            next
        }
        /^[[:space:]]*($|#)/ { next }
        {
            entry = $0
            owner = default_owner
            for (rule_index = 1; rule_index <= rule_count; rule_index++) {
                pattern = rule_pattern[rule_index]
                if (pattern ~ /\/\*\*$/) {
                    root = substr(pattern, 1, length(pattern) - 3)
                    if (entry == root || substr(entry, 1, length(root) + 1) == root "/") {
                        owner = rule_owner[rule_index]
                        break
                    }
                } else if (entry == pattern) {
                    owner = rule_owner[rule_index]
                    break
                }
            }
            if (owner != "distribution") {
                print entry > "/dev/stderr"
                invalid = 1
            }
        }
        END {
            if (default_owner == "" || resolution != "first-match" || rule_count == 0) {
                invalid = 1
            }
            exit invalid
        }
    ' "$ownership_file" "$manifest_file"; then
        fail "distribution manifest contains a path not owned by distribution"
    fi
}

# Verify that the SHA-256 manifest covers all assets and every digest matches.
validate_checksums() {
    checksum_file=$skill_directory/checksums/workspace-v0.1.sha256
    [ -s "$checksum_file" ] || fail "missing workspace checksum manifest"

    if ! awk '
        {
            checksum = $1
            path = $0
            sub(/^[^[:space:]]+[[:space:]][[:space:]]/, "", path)
            if (length(checksum) != 64 || checksum !~ /^[[:xdigit:]]+$/ || path == $0 || path == "") {
                exit 1
            }
        }
    ' "$checksum_file"; then
        fail "malformed workspace checksum manifest"
    fi

    if ! awk '
        {
            path = $0
            sub(/^[^[:space:]]+[[:space:]][[:space:]]/, "", path)
            print path
        }
    ' "$checksum_file" | while IFS= read -r checksum_path || [ -n "$checksum_path" ]; do
        case "$checksum_path" in
            ""|/*|.|..|./*|../*|*/./*|*/../*|*/.|*/..|*//*|*[[:space:]]*) exit 1 ;;
        esac
    done; then
        fail "unsafe path in workspace checksum manifest"
    fi

    actual_files=$(
        cd "$asset_directory"
        find . -type f -print | sed 's#^\./##' | LC_ALL=C sort
    )
    checksummed_files=$(awk '
        {
            path = $0
            sub(/^[^[:space:]]+[[:space:]][[:space:]]/, "", path)
            print path
        }
    ' "$checksum_file" | LC_ALL=C sort)
    [ "$actual_files" = "$checksummed_files" ] || fail "checksum manifest does not cover the exact asset file set"

    if command -v sha256sum >/dev/null 2>&1; then
        (cd "$asset_directory" && sha256sum -c "$checksum_file" >/dev/null 2>&1) || fail "workspace asset checksum mismatch"
    elif command -v shasum >/dev/null 2>&1; then
        (cd "$asset_directory" && shasum -a 256 -c "$checksum_file" >/dev/null 2>&1) || fail "workspace asset checksum mismatch"
    else
        fail "SHA-256 verification requires sha256sum or shasum"
    fi

}

script_directory=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
skill_directory=$(CDPATH='' cd "$script_directory/.." && pwd -P)
bundle_file=$skill_directory/bundle.toml
asset_directory=$skill_directory/assets/workspace-v0.1

[ -s "$skill_directory/SKILL.md" ] || fail "missing external SKILL.md"
[ -s "$skill_directory/agents/openai.yaml" ] || fail "missing agents/openai.yaml"
[ -s "$bundle_file" ] || fail "missing bundle.toml"
[ -d "$asset_directory" ] || fail "missing asset root: $asset_directory"
[ -x "$script_directory/create-workspace.sh" ] || fail "create script is not executable"
[ -x "$script_directory/validate-workspace.sh" ] || fail "workspace validator is not executable"
[ -x "$script_directory/plan-repair.sh" ] || fail "repair planner is not executable"
[ -s "$script_directory/create-workspace.ps1" ] || fail "PowerShell create script is missing"
[ -s "$script_directory/validate-workspace.ps1" ] || fail "PowerShell workspace validator is missing"
[ -s "$script_directory/plan-repair.ps1" ] || fail "PowerShell repair planner is missing"
[ -s "$script_directory/validate-bundle.ps1" ] || fail "PowerShell bundle validator is missing"
placeholder_marker=TO"DO"
if grep -F "$placeholder_marker" "$skill_directory/SKILL.md" >/dev/null 2>&1; then
    fail "external Skill contains an unresolved template placeholder"
fi

validate_bundle_metadata
require_exact_line 'id = "bootstrap-workcell"' "$bundle_file"
require_exact_line 'version = "1.0.0"' "$bundle_file"
require_exact_line 'status = "stable"' "$bundle_file"
require_exact_line 'format = "text-only-skill-bundle"' "$bundle_file"
require_exact_line 'workspace = "0.1"' "$bundle_file"
require_exact_line 'release_manifest = "0.1"' "$bundle_file"
require_exact_line 'environment_facts = "0.1"' "$bundle_file"
require_exact_line 'project_plugin = "0.1"' "$bundle_file"
require_exact_line 'diagnostic_profile = "0.1"' "$bundle_file"
require_exact_line 'task = "0.1"' "$bundle_file"
require_exact_line 'feedback_report = "0.1"' "$bundle_file"
require_exact_line 'project_plugin_api = "0.1"' "$bundle_file"
require_exact_line 'diagnostic_plugin_api = "0.1"' "$bundle_file"
require_exact_line 'workspace_asset = "assets/workspace-v0.1"' "$bundle_file"
require_exact_line 'network_default = "deny"' "$bundle_file"
require_exact_line 'install_tools = false' "$bundle_file"
require_exact_line 'modify_shell = false' "$bundle_file"
require_exact_line 'overwrite_non_empty = false' "$bundle_file"
require_exact_line 'self_update = false' "$bundle_file"
require_exact_line 'name: bootstrap-workcell' "$skill_directory/SKILL.md"
require_exact_line '  display_name: "Bootstrap Workcell"' "$skill_directory/agents/openai.yaml"

first_link=$(find "$asset_directory" -type l -print | sed -n '1p')
[ -z "$first_link" ] || fail "symbolic links are not allowed in V0.1 assets: $first_link"
first_special=$(find "$asset_directory" ! -type d ! -type f -print | sed -n '1p')
[ -z "$first_special" ] || fail "special files are not allowed in V0.1 assets: $first_special"
first_cache=$(find "$asset_directory" \( \
    -name __pycache__ -o \
    -name '*.pyc' -o \
    -name '*.pyo' -o \
    -name .DS_Store -o \
    -name .pytest_cache -o \
    -name .mypy_cache -o \
    -name .ruff_cache \
\) -print | sed -n '1p')
[ -z "$first_cache" ] || fail "generated cache is not allowed in V0.1 assets: $first_cache"

for runtime_name in \
    initialize-workcell \
    inspect-host-environment \
    adapt-project-workspace \
    configure-project-diagnostics \
    workcell-doctor \
    start-workcell-task \
    upgrade-workcell \
    extract-workcell-feedback \
    localize-workcell
do
    validate_runtime_skill "$runtime_name"
done

validate_manifest_ownership
validate_checksums
"$script_directory/validate-workspace.sh" "$asset_directory"
echo "VALID: bundle $skill_directory"
