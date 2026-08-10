#!/bin/sh
set -eu

# Print create-script usage.
usage() {
    echo "Usage: $0 <empty-or-absent-target-directory>" >&2
}

# Determine whether a directory is empty, including regular, hidden, and symlink entries.
is_empty_directory() {
    check_directory=$1
    for check_entry in \
        "$check_directory"/* \
        "$check_directory"/.[!.]* \
        "$check_directory"/..?*
    do
        if [ -e "$check_entry" ] || [ -L "$check_entry" ]; then
            return 1
        fi
    done
    return 0
}

# Clean only the constrained staging directory created by this run.
cleanup_stage() {
    if [ -n "${stage_directory:-}" ] && [ -d "$stage_directory" ]; then
        rm -rf "$stage_directory"
    fi
}

# Read the directory inode to distinguish same-directory rename from a raced move-into.
directory_identity() {
    # shellcheck disable=SC2012
    ls -di "$1" 2>/dev/null | awk 'NR == 1 { print $1 }'
}

if [ "$#" -ne 1 ]; then
    usage
    exit 2
fi

requested_target=$1
case "$requested_target" in
    ""|/|.|..)
        echo "ERROR: target must be an explicit workspace directory, not '$requested_target'." >&2
        exit 2
        ;;
esac

script_directory=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
skill_directory=$(CDPATH='' cd "$script_directory/.." && pwd -P)
asset_directory=$skill_directory/assets/workspace-v0.1

"$script_directory/validate-bundle.sh" >/dev/null

target_parent_input=$(dirname "$requested_target")
target_name=$(basename "$requested_target")
case "$target_name" in
    ""|.|..)
        echo "ERROR: target basename is unsafe: '$target_name'." >&2
        exit 2
        ;;
esac

mkdir -p "$target_parent_input"
target_parent=$(CDPATH='' cd "$target_parent_input" && pwd -P)
target_directory=$target_parent/$target_name

if [ -L "$target_directory" ]; then
    echo "ERROR: target must not be a symbolic link: $target_directory" >&2
    exit 1
fi

target_preexisted=false
if [ -e "$target_directory" ]; then
    if [ ! -d "$target_directory" ]; then
        echo "ERROR: target exists and is not a directory: $target_directory" >&2
        exit 1
    fi
    if ! is_empty_directory "$target_directory"; then
        echo "ERROR: refusing to overwrite non-empty target: $target_directory" >&2
        exit 1
    fi
    target_preexisted=true
fi

stage_directory=$target_parent/.$target_name.bootstrap.$$
if [ -e "$stage_directory" ] || [ -L "$stage_directory" ]; then
    echo "ERROR: staging path already exists: $stage_directory" >&2
    exit 2
fi

trap cleanup_stage 0 1 2 15
mkdir "$stage_directory"
cp -R "$asset_directory"/. "$stage_directory"
"$script_directory/validate-workspace.sh" "$stage_directory" >/dev/null

if [ "$target_preexisted" = true ]; then
    if ! rmdir "$target_directory"; then
        echo "ERROR: target changed after the emptiness check: $target_directory" >&2
        exit 1
    fi
fi

if [ -e "$target_directory" ] || [ -L "$target_directory" ]; then
    echo "ERROR: target appeared during staged installation: $target_directory" >&2
    exit 1
fi

stage_identity=$(directory_identity "$stage_directory")
[ -n "$stage_identity" ] || {
    echo "ERROR: unable to identify staged workspace: $stage_directory" >&2
    exit 2
}
stage_name=$(basename "$stage_directory")

if ! mv "$stage_directory" "$target_directory"; then
    if [ "$target_preexisted" = true ] && [ ! -e "$target_directory" ]; then
        mkdir "$target_directory"
    fi
    echo "ERROR: failed to install staged workspace at: $target_directory" >&2
    exit 2
fi

installed_identity=$(directory_identity "$target_directory")
if [ "$installed_identity" != "$stage_identity" ]; then
    nested_stage=$target_directory/$stage_name
    nested_identity=$(directory_identity "$nested_stage")
    if [ "$nested_identity" = "$stage_identity" ]; then
        if ! mv "$nested_stage" "$stage_directory"; then
            stage_directory=
            echo "ERROR: target raced with installation; staged content remains at: $nested_stage" >&2
            exit 2
        fi
    else
        stage_directory=
    fi
    echo "ERROR: target raced with installation; refusing successful completion: $target_directory" >&2
    exit 1
fi

stage_directory=
trap - 0 1 2 15
echo "CREATED: $target_directory"
