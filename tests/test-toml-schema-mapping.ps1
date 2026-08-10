#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillRoot = Join-Path $repoRoot 'skills/bootstrap-workcell'
$assetRoot = Join-Path $skillRoot 'assets/workspace-v0.1'
$testRoot = New-TestDirectory -Prefix 'workcell-toml-schema'

function Test-TomlInstance {
    param([string]$SchemaName, [string]$TomlPath)
    $jsonPath = Join-Path $testRoot "$SchemaName.json"
    $jsonLines = @(Invoke-Python3 -Arguments @((Join-Path $repoRoot 'scripts/toml-to-json.py'), $TomlPath))
    Write-Utf8NoBom -Path $jsonPath -Content (($jsonLines -join "`n") + "`n")
    Invoke-Node -Arguments @(
        (Join-Path $repoRoot 'scripts/validate-json-instance.mjs'),
        (Join-Path $repoRoot "schemas/$SchemaName.schema.json"), $jsonPath
    ) | Out-Null
}

try {
    Test-TomlInstance -SchemaName 'bundle' -TomlPath (Join-Path $skillRoot 'bundle.toml')
    Test-TomlInstance -SchemaName 'workspace' -TomlPath (Join-Path $assetRoot '.ai-workspace/workspace.toml')
    Test-TomlInstance -SchemaName 'diagnostic-profile' -TomlPath (Join-Path $assetRoot 'project/diagnostics/diagnostic-profile.toml')
    Test-TomlInstance -SchemaName 'task' -TomlPath (Join-Path $assetRoot '.ai-workspace/templates/task.toml')
    Write-Output 'Validated TOML-to-Schema mappings.'
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
