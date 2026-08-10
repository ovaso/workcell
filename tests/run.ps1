#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$powerShell = (Get-Process -Id $PID).Path

foreach ($testScript in @(
    'test-canonical-english.ps1',
    'test-powershell-parity.ps1',
    'test-schema-validation.ps1',
    'test-release-manifest.ps1',
    'test-validate-skill.py',
    'test-skills.ps1',
    'test-github-config.py',
    'test-runtime-scripts.ps1',
    'test-feedback-integration.py',
    'test-build-sync.ps1',
    'test-bootstrap.ps1',
    'test-product-validation.ps1',
    'test-package.ps1'
)) {
    $path = Join-Path $PSScriptRoot $testScript
    Write-Output "Running $testScript"
    if ($testScript.EndsWith('.ps1')) {
        & $powerShell -NoProfile -ExecutionPolicy Bypass -File $path
    }
    else {
        Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
        Invoke-Python3 -Arguments @($path)
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Output 'All Workcell tests passed.'
