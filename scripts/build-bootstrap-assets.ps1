#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-PythonInvocation {
    foreach ($candidate in @('python3', 'python')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return @{ Command = $command.Source; Prefix = @() }
        }
    }
    $launcher = Get-Command 'py' -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        return @{ Command = $launcher.Source; Prefix = @('-3') }
    }
    throw 'Python 3.11 or newer is required.'
}

function Invoke-Python {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $invocation = Get-PythonInvocation
    $command = $invocation.Command
    $allArguments = @($invocation.Prefix) + $Arguments
    & $command @allArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Copy-DirectoryContent {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

function Replace-Directory {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Target
    )

    $resolvedTarget = [IO.Path]::GetFullPath($Target).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    if (-not $script:AllowedTargets.ContainsKey($resolvedTarget)) {
        throw "Refusing unsafe build target: $resolvedTarget"
    }

    $stage = Join-Path $script:StageRoot ([Guid]::NewGuid().ToString('N'))
    Copy-DirectoryContent -Source $Source -Destination $stage
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $resolvedTarget) -Force | Out-Null
    Move-Item -LiteralPath $stage -Destination $resolvedTarget
}

function Get-RelativeForwardPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $rootPrefix = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $fullPath = [IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes root: $Path"
    }
    return $fullPath.Substring($rootPrefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
}

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillRoot = Join-Path $repoRoot 'skills/bootstrap-standard-workspace'
$assetRoot = Join-Path $skillRoot 'assets/workspace-v0.1'
$stageRoot = Join-Path ([IO.Path]::GetTempPath()) ('std-workspace-build.' + [Guid]::NewGuid().ToString('N'))
$script:StageRoot = $stageRoot
New-Item -ItemType Directory -Path $stageRoot | Out-Null

$allowed = @(
    (Join-Path $skillRoot 'references/product-docs'),
    (Join-Path $skillRoot 'references/product-facts'),
    (Join-Path $skillRoot 'references/schemas'),
    (Join-Path $skillRoot 'references/specs'),
    (Join-Path $skillRoot 'LICENSES'),
    (Join-Path $assetRoot '.ai-workspace/schemas'),
    (Join-Path $assetRoot '.ai-workspace/specs'),
    (Join-Path $assetRoot 'docs/standard')
)
$script:AllowedTargets = @{}
foreach ($target in $allowed) {
    $script:AllowedTargets[[IO.Path]::GetFullPath($target).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)] = $true
}

try {
    Replace-Directory -Source (Join-Path $repoRoot 'specs') -Target (Join-Path $skillRoot 'references/specs')
    Replace-Directory -Source (Join-Path $repoRoot 'schemas') -Target (Join-Path $skillRoot 'references/schemas')

    $releaseDocs = Join-Path $stageRoot 'release-product-docs'
    New-Item -ItemType Directory -Path $releaseDocs | Out-Null
    foreach ($document in @('product-vision.md', 'architecture.md', 'lifecycle.md', 'roadmap.md')) {
        Copy-Item -LiteralPath (Join-Path $repoRoot "docs/$document") -Destination (Join-Path $releaseDocs $document)
    }
    Replace-Directory -Source $releaseDocs -Target (Join-Path $skillRoot 'references/product-docs')

    $releaseFacts = Join-Path $stageRoot 'release-product-facts'
    New-Item -ItemType Directory -Path $releaseFacts | Out-Null
    foreach ($fact in @('known-tool-capabilities.toml', 'session-decisions.toml')) {
        Copy-Item -LiteralPath (Join-Path $repoRoot "facts/$fact") -Destination (Join-Path $releaseFacts $fact)
    }
    Replace-Directory -Source $releaseFacts -Target (Join-Path $skillRoot 'references/product-facts')

    Replace-Directory -Source (Join-Path $repoRoot 'LICENSES') -Target (Join-Path $skillRoot 'LICENSES')
    Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination (Join-Path $skillRoot 'LICENSE') -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination (Join-Path $assetRoot 'LICENSE') -Force
    Replace-Directory -Source (Join-Path $repoRoot 'specs') -Target (Join-Path $assetRoot '.ai-workspace/specs')
    Replace-Directory -Source (Join-Path $repoRoot 'schemas') -Target (Join-Path $assetRoot '.ai-workspace/schemas')

    New-Item -ItemType Directory -Path (Join-Path $assetRoot 'knowledge') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot 'facts/known-tool-capabilities.toml') -Destination (Join-Path $assetRoot 'knowledge/tool-capabilities.toml') -Force

    $standardDocs = Join-Path $stageRoot 'standard-docs'
    New-Item -ItemType Directory -Path $standardDocs | Out-Null
    foreach ($document in @('product-vision.md', 'architecture.md', 'lifecycle.md', 'roadmap.md')) {
        Copy-Item -LiteralPath (Join-Path $repoRoot "docs/$document") -Destination (Join-Path $standardDocs $document)
    }
    Replace-Directory -Source $standardDocs -Target (Join-Path $assetRoot 'docs/standard')

    $releaseVersion = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Raw).Trim()
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Invoke-Python -Arguments @(
        (Join-Path $repoRoot 'scripts/generate-release-manifest.py'),
        '--asset-root', $assetRoot,
        '--release-version', $releaseVersion
    )

    $checksumDirectory = Join-Path $skillRoot 'checksums'
    New-Item -ItemType Directory -Path $checksumDirectory -Force | Out-Null
    $checksumPath = Join-Path $checksumDirectory 'workspace-v0.1.sha256'
    $relativeFiles = @(
        Get-ChildItem -LiteralPath $assetRoot -Recurse -File -Force | ForEach-Object {
            Get-RelativeForwardPath -Root $assetRoot -Path $_.FullName
        }
    )
    [Array]::Sort($relativeFiles, [StringComparer]::Ordinal)
    $checksumLines = foreach ($relativePath in $relativeFiles) {
        $nativePath = Join-Path $assetRoot ($relativePath.Replace('/', [IO.Path]::DirectorySeparatorChar))
        $digest = (Get-FileHash -LiteralPath $nativePath -Algorithm SHA256).Hash.ToLowerInvariant()
        "$digest  $relativePath"
    }
    $utf8NoBom = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($checksumPath, (($checksumLines -join "`n") + "`n"), $utf8NoBom)

    Write-Output "Bootstrap assets synchronized for product $releaseVersion"
}
finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
