#!/bin/sh
set -eu

# Print a test failure and exit immediately.
fail() {
    echo "TEST FAILED: $*" >&2
    exit 1
}

# Clean only the isolated test directory created by mktemp.
cleanup() {
    if [ -n "${test_root:-}" ] && [ -d "$test_root" ]; then
        rm -rf "$test_root"
    fi
}

# Determine whether the test directory is still empty, including hidden and symlink entries.
is_empty_directory() {
    empty_check_directory=$1
    for empty_check_entry in \
        "$empty_check_directory"/* \
        "$empty_check_directory"/.[!.]* \
        "$empty_check_directory"/..?*
    do
        if [ -e "$empty_check_entry" ] || [ -L "$empty_check_entry" ]; then
            return 1
        fi
    done
    return 0
}

test_directory=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
skill_directory=$(CDPATH='' cd "$test_directory/.." && pwd -P)
script_directory=$skill_directory/scripts
asset_directory=$skill_directory/assets/workspace-v0.1
test_root=$(mktemp -d "${TMPDIR:-/tmp}/bootstrap-workcell.XXXXXX")
trap cleanup 0 1 2 15

"$script_directory/validate-bundle.sh" >/dev/null

bundle_metadata_skill=$test_root/bundle-metadata-skill
bundle_metadata_original=$test_root/bundle.original.toml
cp -R "$skill_directory" "$bundle_metadata_skill"
cp "$bundle_metadata_skill/bundle.toml" "$bundle_metadata_original"

sed 's/^\[bundle\]$/[wrong-section]/' "$bundle_metadata_original" > "$bundle_metadata_skill/bundle.toml"
if "$bundle_metadata_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted an invalid section"
fi

awk '
    /^\[versions\]$/ { print "id = \"bootstrap-workcell\"" }
    { print }
' "$bundle_metadata_original" > "$bundle_metadata_skill/bundle.toml"
if "$bundle_metadata_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted a duplicate key"
fi

sed 's/^install_tools = false$/install_tools = "false"/' "$bundle_metadata_original" > "$bundle_metadata_skill/bundle.toml"
if "$bundle_metadata_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted a boolean encoded as a string"
fi

sed '/^required_entries = \[$/,/^]$/d' "$bundle_metadata_original" > "$bundle_metadata_skill/bundle.toml"
if "$bundle_metadata_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted a missing required_entries array"
fi

sed '/^[[:space:]]*"\.ai-workspace\/release-manifest.json",$/d' "$bundle_metadata_original" > "$bundle_metadata_skill/bundle.toml"
if "$bundle_metadata_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted a missing Release manifest required entry"
fi

tampered_skill=$test_root/tampered-skill
cp -R "$skill_directory" "$tampered_skill"
echo "checksum-tamper-test" >> "$tampered_skill/assets/workspace-v0.1/AI_WORKSPACE.md"
if "$tampered_skill/scripts/validate-bundle.sh" >/dev/null 2>&1; then
    fail "bundle validator accepted a checksum mismatch"
fi

created_workspace=$test_root/created-workspace
create_output=$("$script_directory/create-workspace.sh" "$created_workspace")
case "$create_output" in
    CREATED:*) ;;
    *) fail "create script did not report CREATED" ;;
esac
"$script_directory/validate-workspace.sh" "$created_workspace" >/dev/null
diff -r "$asset_directory" "$created_workspace" >/dev/null || fail "created workspace differs from release asset"

invalid_metadata_workspace=$test_root/invalid-metadata-workspace
cp -R "$created_workspace" "$invalid_metadata_workspace"
workspace_metadata_original=$test_root/workspace.original.toml
versions_metadata_original=$test_root/versions.original.lock
cp "$invalid_metadata_workspace/.ai-workspace/workspace.toml" "$workspace_metadata_original"
cp "$invalid_metadata_workspace/.ai-workspace/versions.lock" "$versions_metadata_original"

sed 's/^\[workspace\]$/[wrong-section]/' "$workspace_metadata_original" > "$invalid_metadata_workspace/.ai-workspace/workspace.toml"
if "$script_directory/validate-workspace.sh" --metadata-only "$invalid_metadata_workspace" >/dev/null 2>&1; then
    fail "workspace validator accepted an invalid section"
fi

sed 's/^overwrite_non_empty = false$/overwrite_non_empty = "false"/' "$workspace_metadata_original" > "$invalid_metadata_workspace/.ai-workspace/workspace.toml"
if "$script_directory/validate-workspace.sh" --metadata-only "$invalid_metadata_workspace" >/dev/null 2>&1; then
    fail "workspace validator accepted a boolean encoded as a string"
fi

cp "$workspace_metadata_original" "$invalid_metadata_workspace/.ai-workspace/workspace.toml"
awk '
    /^\[release\]$/ { print "product = \"0.2.0\"" }
    { print }
' "$versions_metadata_original" > "$invalid_metadata_workspace/.ai-workspace/versions.lock"
if "$script_directory/validate-workspace.sh" --metadata-only "$invalid_metadata_workspace" >/dev/null 2>&1; then
    fail "workspace validator accepted a duplicate version key"
fi

sed 's/^project_plugin_api = "0.1"$/project_plugin_api = "0.2"/' "$versions_metadata_original" > "$invalid_metadata_workspace/.ai-workspace/versions.lock"
if "$script_directory/validate-workspace.sh" --metadata-only "$invalid_metadata_workspace" >/dev/null 2>&1; then
    fail "workspace validator accepted an incompatible plugin API version"
fi

cp "$workspace_metadata_original" "$invalid_metadata_workspace/.ai-workspace/workspace.toml"
sed 's/^release_manifest_schema = "0.1"$/release_manifest_schema = "0.2"/' "$versions_metadata_original" > "$invalid_metadata_workspace/.ai-workspace/versions.lock"
if "$script_directory/validate-workspace.sh" --metadata-only "$invalid_metadata_workspace" >/dev/null 2>&1; then
    fail "workspace validator accepted an incompatible Release manifest Schema version"
fi

existing_empty_workspace=$test_root/existing-empty-workspace
mkdir "$existing_empty_workspace"
"$script_directory/create-workspace.sh" "$existing_empty_workspace" >/dev/null
"$script_directory/validate-workspace.sh" "$existing_empty_workspace" >/dev/null

external_specs=$test_root/external-specs
mv "$existing_empty_workspace/.ai-workspace/specs" "$external_specs"
ln -s "$external_specs" "$existing_empty_workspace/.ai-workspace/specs"
symlink_validation_status=0
"$script_directory/validate-workspace.sh" "$existing_empty_workspace" >/dev/null 2>&1 || symlink_validation_status=$?
[ "$symlink_validation_status" -eq 1 ] || fail "workspace validator did not reject a managed ancestor symlink as drift"
symlink_repair_output=$test_root/symlink-repair-plan.txt
if "$script_directory/plan-repair.sh" "$existing_empty_workspace" > "$symlink_repair_output"; then
    fail "repair planner accepted a managed ancestor symlink"
fi
awk -F '\t' '
    $1 == "TYPE_MISMATCH" && $2 == ".ai-workspace/specs" { found = 1 }
    END { exit(found ? 0 : 1) }
' "$symlink_repair_output" || fail "repair planner did not classify the ancestor symlink"

nonempty_workspace=$test_root/nonempty-workspace
mkdir "$nonempty_workspace"
echo "preserve me" > "$nonempty_workspace/user-file.txt"
if "$script_directory/create-workspace.sh" "$nonempty_workspace" >/dev/null 2>&1; then
    fail "create script accepted a non-empty target"
fi
[ "$(cat "$nonempty_workspace/user-file.txt")" = "preserve me" ] || fail "non-empty target was modified"

symlink_target_directory=$test_root/symlink-target-directory
symlink_workspace=$test_root/symlink-workspace
mkdir "$symlink_target_directory"
ln -s "$symlink_target_directory" "$symlink_workspace"
if "$script_directory/create-workspace.sh" "$symlink_workspace" >/dev/null 2>&1; then
    fail "create script accepted a symbolic-link target"
fi

race_bin=$test_root/race-bin
race_target=$test_root/race-workspace
race_marker=$test_root/race-triggered
real_mv=$(command -v mv)
mkdir "$race_bin"
cp "$test_directory/fixtures/mv-race-wrapper.sh" "$race_bin/mv"
chmod +x "$race_bin/mv"
race_status=0
race_output=$(PATH="$race_bin:$PATH" \
    BOOTSTRAP_REAL_MV="$real_mv" \
    BOOTSTRAP_RACE_MARKER="$race_marker" \
    BOOTSTRAP_RACE_TARGET="$race_target" \
    "$script_directory/create-workspace.sh" "$race_target" 2>&1) || race_status=$?
[ "$race_status" -ne 0 ] || fail "create script reported success during a target race"
case "$race_output" in
    *CREATED:*) fail "create script emitted CREATED during a target race" ;;
esac
[ -d "$race_target" ] || fail "race fixture target was unexpectedly removed"
is_empty_directory "$race_target" || fail "staged workspace was merged into the raced target"

managed_file=
while IFS= read -r managed_path || [ -n "$managed_path" ]; do
    case "$managed_path" in
        ""|\#*) continue ;;
    esac
    if [ -f "$created_workspace/$managed_path" ]; then
        managed_file=$managed_path
        break
    fi
done < "$created_workspace/.ai-workspace/distribution.manifest"
[ -n "$managed_file" ] || fail "manifest contains no managed regular file"

echo "repair-plan-test" >> "$created_workspace/$managed_file"
validation_status=0
"$script_directory/validate-workspace.sh" "$created_workspace" >/dev/null 2>&1 || validation_status=$?
[ "$validation_status" -eq 1 ] || fail "workspace validator did not use drift exit code 1"

repair_output=$test_root/repair-plan.txt
if "$script_directory/plan-repair.sh" "$created_workspace" > "$repair_output"; then
    fail "repair planner did not signal drift"
fi
awk -F '\t' -v expected_path="$managed_file" '
    $1 == "MODIFIED" && $2 == expected_path { found = 1 }
    END { exit(found ? 0 : 1) }
' "$repair_output" || fail "repair planner did not report modified managed file"

cp "$asset_directory/$managed_file" "$created_workspace/$managed_file"
echo "# manifest drift" >> "$created_workspace/.ai-workspace/distribution.manifest"
if "$script_directory/plan-repair.sh" "$created_workspace" > "$repair_output"; then
    fail "repair planner trusted a modified workspace manifest"
fi
awk -F '\t' '
    $1 == "MODIFIED" && $2 == ".ai-workspace/distribution.manifest" { found = 1 }
    END { exit(found ? 0 : 1) }
' "$repair_output" || fail "repair planner did not use the bundle manifest as source of truth"

echo "TEST PASSED: metadata attacks, containment, race refusal, integrity, create, validate, and repair planning"
