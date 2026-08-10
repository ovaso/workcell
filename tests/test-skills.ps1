#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillRoot = Join-Path $repoRoot 'skills/bootstrap-workcell'
$quickValidate = $env:WORKCELL_QUICK_VALIDATE
$explicitQuickValidate = -not [string]::IsNullOrWhiteSpace($quickValidate)
if ([string]::IsNullOrWhiteSpace($quickValidate)) {
    $codexHome = $env:CODEX_HOME
    if ([string]::IsNullOrWhiteSpace($codexHome)) { $codexHome = Join-Path $HOME '.codex' }
    $quickValidate = Join-Path $codexHome 'skills/.system/skill-creator/scripts/quick_validate.py'
}
$officialValidatorAvailable = Test-Path -LiteralPath $quickValidate -PathType Leaf
if ($explicitQuickValidate -and -not $officialValidatorAvailable) { throw "Skill Creator quick_validate.py is unavailable: $quickValidate" }
if ($env:WORKCELL_REQUIRE_OFFICIAL_SKILL_VALIDATOR -eq '1' -and -not $officialValidatorAvailable) {
    throw "Skill Creator quick_validate.py is required but unavailable: $quickValidate"
}

function Test-OneSkill {
    param([string]$SkillPath)
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Invoke-Python3 -Arguments @((Join-Path $repoRoot 'scripts/validate-skill.py'), $SkillPath) | Out-Null
    if ($officialValidatorAvailable) {
        $env:PYTHONPATH = Join-Path $repoRoot 'tests/compat'
        Invoke-Python3 -Arguments @($quickValidate, $SkillPath) | Out-Null
    }
    $metadata = Join-Path $SkillPath 'agents/openai.yaml'
    if (-not (Test-Path -LiteralPath $metadata -PathType Leaf) -or (Get-Item -LiteralPath $metadata).Length -eq 0) { throw "Missing agents/openai.yaml: $SkillPath" }
    $env:PYTHONPATH = ''
    Invoke-Python3 -Arguments @((Join-Path $repoRoot 'scripts/validate-openai-metadata.py'), $SkillPath) | Out-Null
}

Test-OneSkill -SkillPath $skillRoot
Test-OneSkill -SkillPath (Join-Path $repoRoot 'skills/integrate-workcell-feedback')
foreach ($skill in Get-ChildItem -LiteralPath (Join-Path $skillRoot 'assets/workspace-v0.1/skills') -Directory -Force) {
    Test-OneSkill -SkillPath $skill.FullName
}
if ($officialValidatorAvailable) {
    Write-Output 'All Bootstrap and runtime Skills passed repository and official quick validation.'
}
else {
    Write-Output 'All Bootstrap and runtime Skills passed self-contained repository validation.'
}
