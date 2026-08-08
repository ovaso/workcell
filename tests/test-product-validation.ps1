#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$actual = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'facts') -File -Force | ForEach-Object { $_.Name })
[Array]::Sort($actual, [StringComparer]::Ordinal)
$expected = @('known-tool-capabilities.toml', 'session-decisions.toml')
[Array]::Sort($expected, [StringComparer]::Ordinal)
if (($actual -join "`n") -cne ($expected -join "`n")) { throw 'Facts directory must only contain reusable standard facts.' }

& (Join-Path $repoRoot 'scripts/validate-product.ps1')
& (Join-Path $repoRoot 'skills/bootstrap-standard-workspace/scripts/validate-bundle.ps1') | Out-Null
