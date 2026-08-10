#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$assetRoot = Join-Path $repoRoot 'skills/bootstrap-workcell/assets/workspace-v0.1'
$testRoot = New-TestDirectory -Prefix 'workcell-runtime-contracts'
$env:PYTHONDONTWRITEBYTECODE = '1'

try {
    Invoke-Node -Arguments @(
        (Join-Path $repoRoot 'scripts/validate-json-instance.mjs'),
        (Join-Path $repoRoot 'schemas/environment-facts.schema.json'),
        (Join-Path $assetRoot 'environment/current/host-facts.json')
    ) | Out-Null
    $environmentJson = Join-Path $testRoot 'environment.json'
    Invoke-Python3 -Arguments @(
        (Join-Path $assetRoot 'skills/inspect-host-environment/scripts/inspect_host.py'),
        '--context', 'ai-execution', '--no-default-commands', '--skip-environment-names', '--output', $environmentJson
    )
    Invoke-Node -Arguments @(
        (Join-Path $repoRoot 'scripts/validate-json-instance.mjs'),
        (Join-Path $repoRoot 'schemas/environment-facts.schema.json'), $environmentJson
    ) | Out-Null
    $projectJson = Join-Path $testRoot 'project-plugin.json'
    Invoke-Python3 -Arguments @(
        (Join-Path $assetRoot 'skills/adapt-project-workspace/scripts/build_project_plugin.py'),
        '--input', (Join-Path $assetRoot '.ai-workspace/templates/project-plugin.json'), '--output', $projectJson
    )
    Invoke-Node -Arguments @(
        (Join-Path $repoRoot 'scripts/validate-json-instance.mjs'),
        (Join-Path $repoRoot 'schemas/project-plugin.schema.json'), $projectJson
    ) | Out-Null
    Write-Output 'Runtime environment and project contracts passed.'
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
