#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workcell.TestHelpers.psm1') -Force
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillRoot = Join-Path $repoRoot 'skills/bootstrap-workcell'
$assetRoot = Join-Path $skillRoot 'assets/workspace-v0.1'
$testRoot = New-TestDirectory -Prefix 'workcell-build-sync'

function Assert-ExactFiles {
    param([string]$Directory, [string[]]$Expected)
    $actual = @(Get-ChildItem -LiteralPath $Directory -Recurse -File -Force | ForEach-Object { Get-RelativeForwardPath -Root $Directory -Path $_.FullName })
    [Array]::Sort($actual, [StringComparer]::Ordinal)
    [Array]::Sort($Expected, [StringComparer]::Ordinal)
    if (($actual -join "`n") -cne ($Expected -join "`n")) { throw "Unexpected generated file set in $Directory" }
}

function Assert-GeneratedAssets {
    Assert-DirectoriesEqual -Left (Join-Path $repoRoot 'specs') -Right (Join-Path $skillRoot 'references/specs')
    Assert-DirectoriesEqual -Left (Join-Path $repoRoot 'schemas') -Right (Join-Path $skillRoot 'references/schemas')
    Assert-ExactFiles -Directory (Join-Path $skillRoot 'references/product-docs') -Expected @('architecture.md', 'lifecycle.md', 'product-vision.md', 'roadmap.md')
    foreach ($document in @('architecture.md', 'lifecycle.md', 'product-vision.md', 'roadmap.md')) {
        Assert-FilesEqual -Left (Join-Path $repoRoot "docs/$document") -Right (Join-Path $skillRoot "references/product-docs/$document")
        Assert-FilesEqual -Left (Join-Path $repoRoot "docs/$document") -Right (Join-Path $assetRoot "docs/workcell/$document")
    }
    Assert-ExactFiles -Directory (Join-Path $skillRoot 'references/product-facts') -Expected @('known-tool-capabilities.toml', 'session-decisions.toml')
    foreach ($fact in @('known-tool-capabilities.toml', 'session-decisions.toml')) {
        Assert-FilesEqual -Left (Join-Path $repoRoot "facts/$fact") -Right (Join-Path $skillRoot "references/product-facts/$fact")
    }
    Assert-DirectoriesEqual -Left (Join-Path $repoRoot 'LICENSES') -Right (Join-Path $skillRoot 'LICENSES')
    Assert-FilesEqual -Left (Join-Path $repoRoot 'LICENSE') -Right (Join-Path $skillRoot 'LICENSE')
    Assert-FilesEqual -Left (Join-Path $repoRoot 'LICENSE') -Right (Join-Path $assetRoot 'LICENSE')
    Assert-DirectoriesEqual -Left (Join-Path $repoRoot 'specs') -Right (Join-Path $assetRoot '.ai-workspace/specs')
    Assert-DirectoriesEqual -Left (Join-Path $repoRoot 'schemas') -Right (Join-Path $assetRoot '.ai-workspace/schemas')
    Assert-FilesEqual -Left (Join-Path $repoRoot 'facts/known-tool-capabilities.toml') -Right (Join-Path $assetRoot 'knowledge/tool-capabilities.toml')

    $releaseVersion = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Raw).Trim()
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Invoke-Python3 -Arguments @(
        (Join-Path $repoRoot 'scripts/generate-release-manifest.py'), '--asset-root', $assetRoot,
        '--release-version', $releaseVersion, '--check'
    )
    Invoke-Node -Arguments @(
        (Join-Path $repoRoot 'scripts/validate-json-instance.mjs'),
        (Join-Path $repoRoot 'schemas/release-manifest.schema.json'),
        (Join-Path $assetRoot '.ai-workspace/release-manifest.json')
    ) | Out-Null
    $checksum = Join-Path $skillRoot 'checksums/workspace-v0.1.sha256'
    if (-not (Test-Path -LiteralPath $checksum -PathType Leaf) -or (Get-Item -LiteralPath $checksum).Length -eq 0) { throw 'Workspace checksum manifest was not generated.' }
    & (Join-Path $skillRoot 'scripts/validate-bundle.ps1') | Out-Null
}

try {
    Assert-GeneratedAssets
    $savedManifest = Join-Path $testRoot 'release-manifest.json'
    $savedChecksums = Join-Path $testRoot 'workspace-v0.1.sha256'
    Copy-Item -LiteralPath (Join-Path $assetRoot '.ai-workspace/release-manifest.json') -Destination $savedManifest
    Copy-Item -LiteralPath (Join-Path $skillRoot 'checksums/workspace-v0.1.sha256') -Destination $savedChecksums
    & (Join-Path $repoRoot 'scripts/build-bootstrap-assets.ps1')
    Assert-FilesEqual -Left $savedManifest -Right (Join-Path $assetRoot '.ai-workspace/release-manifest.json')
    Assert-FilesEqual -Left $savedChecksums -Right (Join-Path $skillRoot 'checksums/workspace-v0.1.sha256')
    Assert-GeneratedAssets
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
