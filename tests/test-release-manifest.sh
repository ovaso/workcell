#!/bin/sh
set -eu

# Run Release-manifest generator tests without creating Python caches.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 "$script_dir/test-release-manifest.py"
