#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$gitRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot '.git')).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

$missing = New-Object Collections.Generic.List[string]
foreach ($shellScript in Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Filter '*.sh' -Force) {
    if ($shellScript.FullName.StartsWith($gitRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
    $counterpart = [IO.Path]::ChangeExtension($shellScript.FullName, '.ps1')
    if (-not (Test-Path -LiteralPath $counterpart -PathType Leaf)) { $missing.Add($counterpart) }
}
if ($missing.Count -gt 0) { throw "Missing PowerShell counterparts:`n$($missing -join "`n")" }

$parseErrors = New-Object Collections.Generic.List[string]
foreach ($powerShellScript in Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Filter '*.ps1' -Force) {
    if ($powerShellScript.FullName.StartsWith($gitRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
    $tokens = $null
    $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($powerShellScript.FullName, [ref]$tokens, [ref]$errors)
    foreach ($error in $errors) { $parseErrors.Add("$($powerShellScript.FullName): $($error.Message)") }
}
if ($parseErrors.Count -gt 0) { throw "PowerShell syntax errors:`n$($parseErrors -join "`n")" }
Write-Output 'Every POSIX shell script has a syntactically valid PowerShell counterpart.'
