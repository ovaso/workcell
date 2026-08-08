#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$DistDirectory = $env:STD_WORKSPACE_DIST_DIR
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$version = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Raw).Trim()
$skillName = 'bootstrap-standard-workspace'
if ([string]::IsNullOrWhiteSpace($DistDirectory)) {
    $DistDirectory = Join-Path $repoRoot 'dist'
}
$distRoot = [IO.Path]::GetFullPath($DistDirectory)
$archive = Join-Path $distRoot "$skillName-$version.zip"

& (Join-Path $repoRoot 'scripts/build-bootstrap-assets.ps1')
& (Join-Path $repoRoot 'scripts/validate-product.ps1')
& (Join-Path $repoRoot 'skills/bootstrap-standard-workspace/scripts/validate-bundle.ps1') | Out-Null

New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
$checksumPath = "$archive.sha256"
if (Test-Path -LiteralPath $checksumPath) { Remove-Item -LiteralPath $checksumPath -Force }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$skillRoot = Join-Path $repoRoot "skills/$skillName"
$archiveStream = [IO.File]::Open($archive, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
$zip = New-Object IO.Compression.ZipArchive($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $false)
try {
    $rootPrefix = [IO.Path]::GetFullPath($skillRoot).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $files = @(Get-ChildItem -LiteralPath $skillRoot -Recurse -File -Force)
    $entryNames = @($files | ForEach-Object {
        "$skillName/" + $_.FullName.Substring($rootPrefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
    })
    [Array]::Sort($entryNames, $files, [StringComparer]::Ordinal)
    for ($index = 0; $index -lt $files.Count; $index++) {
        $entry = $zip.CreateEntry($entryNames[$index], [IO.Compression.CompressionLevel]::Optimal)
        $entryStream = $entry.Open()
        $sourceStream = [IO.File]::OpenRead($files[$index].FullName)
        try { $sourceStream.CopyTo($entryStream) }
        finally {
            $sourceStream.Dispose()
            $entryStream.Dispose()
        }
    }
}
finally {
    $zip.Dispose()
    $archiveStream.Dispose()
}
$digest = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
$utf8NoBom = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($checksumPath, "$digest  $([IO.Path]::GetFileName($archive))`n", $utf8NoBom)

Write-Output "Created $archive"
