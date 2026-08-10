#!/bin/sh
set -eu

# Reject Han-script text outside runtime locale output, keeping canonical source English-only.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

if rg --hidden -n '[\p{Han}]' \
  --glob '!.git/**' \
  --glob '!skills/bootstrap-workcell/assets/workspace-v0.1/locales/**' \
  "$repo_root"
then
  printf 'Canonical product source contains Han-script text.\n' >&2
  exit 1
fi

printf 'Canonical English source check passed.\n'
