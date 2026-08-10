#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillsRoot = Join-Path $repoRoot 'skills/bootstrap-workcell/assets/workspace-v0.1/skills'
$env:PYTHONDONTWRITEBYTECODE = '1'

foreach ($testFile in @(
    'inspect-host-environment/scripts/test_inspect_host.py',
    'adapt-project-workspace/scripts/test_build_project_plugin.py',
    'workcell-doctor/scripts/test_doctor.py',
    'upgrade-workcell/scripts/test_preview_upgrade.py',
    'extract-workcell-feedback/scripts/test_feedback_report.py'
)) {
    Invoke-Python3 -Arguments @((Join-Path $skillsRoot $testFile))
}
Write-Output 'All runtime Skill script tests passed.'
