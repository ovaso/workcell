#!/bin/sh
set -eu

# Reuse the Bootstrap Skill black-box test against the real distribution directory.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

"$repo_root/skills/bootstrap-workcell/tests/test-bootstrap.sh"
