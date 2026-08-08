#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'StdWorkspace.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$testRoot = New-TestDirectory -Prefix 'std-workspace-package-test'

try {
    & (Join-Path $repoRoot 'scripts/package-bootstrap-skill.ps1') -DistDirectory $testRoot
    $archives = @(Get-ChildItem -LiteralPath $testRoot -File -Filter 'bootstrap-standard-workspace-*.zip')
    if ($archives.Count -ne 1) { throw 'Package was not created uniquely.' }
    $archive = $archives[0]
    $checksumPath = "$($archive.FullName).sha256"
    if ($archive.Length -eq 0 -or -not (Test-Path -LiteralPath $checksumPath -PathType Leaf)) { throw 'Package or checksum was not created.' }
    $checksumLine = (Get-Content -LiteralPath $checksumPath -Raw).Trim()
    if ($checksumLine -notmatch '^([0-9a-f]{64})  (.+)$') { throw 'Package checksum is malformed.' }
    $actualDigest = (Get-FileHash -LiteralPath $archive.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualDigest -cne $Matches[1] -or $Matches[2] -cne $archive.Name) { throw 'Package checksum does not match.' }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($archive.FullName)
    try {
        $entryNames = @($zip.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        foreach ($required in @(
            'bootstrap-standard-workspace/SKILL.md',
            'bootstrap-standard-workspace/LICENSE',
            'bootstrap-standard-workspace/assets/workspace-v0.1/LICENSE',
            'bootstrap-standard-workspace/assets/workspace-v0.1/AI_WORKSPACE.md',
            'bootstrap-standard-workspace/scripts/create-workspace.ps1'
        )) {
            if ($entryNames -cnotcontains $required) { throw "Package is missing $required" }
        }
    }
    finally { $zip.Dispose() }
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
