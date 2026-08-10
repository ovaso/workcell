#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$powerShell = Get-PowerShellExecutable

Invoke-Node -Arguments @((Join-Path $repoRoot 'scripts/validate-schema-examples.mjs'))
Invoke-Node -Arguments @((Join-Path $repoRoot 'tests/test-schema-validator.mjs'))
Invoke-Python3 -Arguments @((Join-Path $repoRoot 'scripts/validate-toml.py'))
foreach ($test in @('test-toml-schema-mapping.ps1', 'test-runtime-contracts.ps1')) {
    & $powerShell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot $test)
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
