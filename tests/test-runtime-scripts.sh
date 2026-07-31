#!/bin/sh
set -eu

# 执行工作区运行时 Skills 携带的确定性脚本单元测试。
script_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd "$script_dir/.." && pwd)
skills_root="$repo_root/skills/bootstrap-standard-workspace/assets/workspace-v0.1/skills"

for test_file in \
  "$skills_root/inspect-host-environment/scripts/test_inspect_host.py" \
  "$skills_root/adapt-project-workspace/scripts/test_build_project_plugin.py" \
  "$skills_root/standard-workspace-doctor/scripts/test_doctor.py" \
  "$skills_root/upgrade-standard-workspace/scripts/test_preview_upgrade.py" \
  "$skills_root/extract-standard-feedback/scripts/test_feedback_report.py"
do
  PYTHONDONTWRITEBYTECODE=1 python3 "$test_file"
done

printf 'All runtime Skill script tests passed.\n'
