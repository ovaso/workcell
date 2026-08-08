#!/bin/sh
set -eu

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

# Run the repository-level offline validation suite.
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)

for test_script in \
  "$script_dir/test-canonical-english.sh" \
  "$script_dir/test-powershell-parity.sh" \
  "$script_dir/test-schema-validation.sh" \
  "$script_dir/test-release-manifest.sh" \
  "$script_dir/test-validate-skill.py" \
  "$script_dir/test-skills.sh" \
  "$script_dir/test-github-config.py" \
  "$script_dir/test-runtime-scripts.sh" \
  "$script_dir/test-feedback-integration.py" \
  "$script_dir/test-build-sync.sh" \
  "$script_dir/test-bootstrap.sh" \
  "$script_dir/test-product-validation.sh" \
  "$script_dir/test-package.sh"
do
  printf 'Running %s\n' "$(basename "$test_script")"
  "$test_script"
done

printf 'All std-workspace tests passed.\n'
