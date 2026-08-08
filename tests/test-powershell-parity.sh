#!/bin/sh
set -eu

# Require a PowerShell counterpart for every POSIX shell script in the product and test surfaces.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

missing=false
find "$repo_root" -path "$repo_root/.git" -prune -o -type f -name '*.sh' -print | LC_ALL=C sort | while IFS= read -r shell_script; do
  powershell_script=${shell_script%.sh}.ps1
  if [ ! -s "$powershell_script" ]; then
    printf 'Missing PowerShell counterpart: %s\n' "$powershell_script" >&2
    missing=true
  fi
done

# The loop may run in a subshell, so perform a second count-based assertion.
shell_count=$(find "$repo_root" -path "$repo_root/.git" -prune -o -type f -name '*.sh' -print | wc -l | tr -d '[:space:]')
paired_count=$(find "$repo_root" -path "$repo_root/.git" -prune -o -type f -name '*.sh' -exec sh -c 'for path do [ -s "${path%.sh}.ps1" ] && printf "."; done' sh {} + | wc -c | tr -d '[:space:]')
if [ "$shell_count" -ne "$paired_count" ]; then
  printf 'Expected %s PowerShell counterparts, found %s.\n' "$shell_count" "$paired_count" >&2
  exit 1
fi

if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -File "$script_dir/test-powershell-parity.ps1"
fi

printf 'PowerShell counterpart coverage passed.\n'
