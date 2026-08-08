#!/bin/sh
set -eu

# Run the complete product structure and safety scan.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)

fact_files=$(cd "$repo_root/facts" && find . -maxdepth 1 -type f -print | sed 's#^./##' | LC_ALL=C sort)
expected_fact_files=$(printf '%s\n' known-tool-capabilities.toml session-decisions.toml | LC_ALL=C sort)
if [ "$fact_files" != "$expected_fact_files" ]; then
  printf 'Facts directory must only contain reusable standard facts.\n' >&2
  exit 1
fi

"$repo_root/scripts/validate-product.sh"
