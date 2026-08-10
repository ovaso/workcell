#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$gitRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot '.git')).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$localeRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'skills/bootstrap-workcell/assets/workspace-v0.1/locales')).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$hanPattern = '[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]'
$matches = New-Object Collections.Generic.List[string]

foreach ($file in Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force) {
    if ($file.FullName.StartsWith($gitRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
    if ($file.FullName.StartsWith($localeRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
    try {
        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $file.FullName -ErrorAction Stop) {
            $lineNumber++
            if ($line -match $hanPattern) { $matches.Add("$($file.FullName):${lineNumber}:$line") }
        }
    }
    catch { }
}
if ($matches.Count -gt 0) {
    $matches | ForEach-Object { [Console]::Error.WriteLine($_) }
    throw 'Canonical product source contains Han-script text.'
}
Write-Output 'Canonical English source check passed.'
