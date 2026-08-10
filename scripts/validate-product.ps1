#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    [Console]::Error.WriteLine($Message)
    exit 1
}

function Get-PythonInvocation {
    foreach ($candidate in @('python3', 'python')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) { return @{ Command = $command.Source; Prefix = @() } }
    }
    $launcher = Get-Command 'py' -ErrorAction SilentlyContinue
    if ($null -ne $launcher) { return @{ Command = $launcher.Source; Prefix = @('-3') } }
    Fail 'Python 3.11 or newer is required.'
}

function Invoke-Python {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $invocation = Get-PythonInvocation
    $command = $invocation.Command
    $allArguments = @($invocation.Prefix) + $Arguments
    & $command @allArguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Require-Path {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot $RelativePath))) {
        Fail "Missing required path: $RelativePath"
    }
}

function Require-ExactLine {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Expected
    )
    if (@(Get-Content -LiteralPath $Path) -cnotcontains $Expected) {
        Fail "Release version metadata mismatch in $Path: expected $Expected"
    }
}

function Find-TextMatch {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Pattern
    )
    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -File -Force) {
        try {
            $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
            if ($content -match $Pattern) { return $file.FullName }
        }
        catch { }
    }
    return $null
}

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:RepoRoot = $repoRoot
$skillRoot = Join-Path $repoRoot 'skills/bootstrap-workcell'
$assetRoot = Join-Path $skillRoot 'assets/workspace-v0.1'
$manifest = Join-Path $assetRoot '.ai-workspace/distribution.manifest'

foreach ($requiredPath in @(
    'README.md',
    'LICENSE',
    'CONTRIBUTING.md',
    'CODE_OF_CONDUCT.md',
    'SECURITY.md',
    'SUPPORT.md',
    'GOVERNANCE.md',
    'VERSION',
    'product.toml',
    '.github/CODEOWNERS',
    '.github/dependabot.yml',
    '.github/workflows/ci.yml',
    '.github/workflows/codeql.yml',
    '.github/workflows/dependency-review.yml',
    '.github/workflows/release-candidate.yml',
    'schemas/release-manifest.schema.json',
    'schemas/examples/release-manifest.example.json',
    'schemas/workspace.schema.json',
    'specs/workspace-spec-v0.1.md',
    'skills/bootstrap-workcell/SKILL.md',
    'skills/bootstrap-workcell/LICENSE',
    'skills/bootstrap-workcell/scripts/create-workspace.ps1',
    'skills/bootstrap-workcell/scripts/validate-workspace.ps1',
    'skills/bootstrap-workcell/assets/workspace-v0.1/AI_WORKSPACE.md',
    'skills/bootstrap-workcell/assets/workspace-v0.1/AGENTS.md',
    'skills/bootstrap-workcell/assets/workspace-v0.1/LICENSE',
    'skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/release-manifest.json',
    'skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/workspace.toml',
    'skills/bootstrap-workcell/assets/workspace-v0.1/.ai-workspace/versions.lock',
    'skills/bootstrap-workcell/assets/workspace-v0.1/knowledge/tool-capabilities.toml'
)) {
    Require-Path $requiredPath
}

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.git') -PathType Container)) {
    Fail 'workcell must be an independent Git repository.'
}

foreach ($line in Get-Content -LiteralPath $manifest) {
    $entry = $line
    if ($entry.Length -eq 0 -or $entry.StartsWith('#')) { continue }
    if (-not (Test-Path -LiteralPath (Join-Path $assetRoot ($entry.Replace('/', [IO.Path]::DirectorySeparatorChar))))) {
        Fail "Distribution manifest points to missing path: $entry"
    }
}

$link = Get-ChildItem -LiteralPath $skillRoot -Recurse -Force | Where-Object {
    ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
} | Select-Object -First 1
if ($null -ne $link) { Fail 'Distributable Bootstrap Skill must not contain symbolic links or junctions.' }

$cache = Get-ChildItem -LiteralPath $skillRoot -Recurse -Force | Where-Object {
    $_.Name -eq '__pycache__' -or $_.Name -in @('.DS_Store', '.pytest_cache', '.mypy_cache', '.ruff_cache') -or $_.Extension -in @('.pyc', '.pyo')
} | Select-Object -First 1
if ($null -ne $cache) { Fail "Generated cache found in distributable Bootstrap Skill: $($cache.FullName)" }

foreach ($skillFile in Get-ChildItem -LiteralPath $skillRoot -Recurse -File -Filter 'SKILL.md') {
    if ((Get-Content -LiteralPath $skillFile.FullName -Raw) -match '\bTODO\b|\[TODO') {
        Fail "Skill placeholder found: $($skillFile.FullName)"
    }
}

$hostPath = Find-TextMatch -Root $skillRoot -Pattern '/Users/|/home/[^/]+/|\\Users\\'
if ($null -ne $hostPath) { Fail "Host-specific absolute path found in distributable Bootstrap Skill: $hostPath" }
$credential = Find-TextMatch -Root $skillRoot -Pattern '-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}'
if ($null -ne $credential) { Fail "Credential-like material found in distributable Bootstrap Skill: $credential" }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $node) { Fail 'Node.js is required for product validation.' }
$nodeCommand = $node.Source
& $nodeCommand (Join-Path $repoRoot 'scripts/validate-schema-examples.mjs')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONDONTWRITEBYTECODE = '1'
Invoke-Python -Arguments @((Join-Path $repoRoot 'scripts/validate-toml.py'))
Invoke-Python -Arguments @((Join-Path $repoRoot 'scripts/validate-github-config.py'))
$releaseVersion = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Raw).Trim()
Require-ExactLine -Path (Join-Path $repoRoot 'product.toml') -Expected "version = `"$releaseVersion`""
Require-ExactLine -Path (Join-Path $skillRoot 'bundle.toml') -Expected "version = `"$releaseVersion`""
foreach ($versionMetadata in @(
    (Join-Path $assetRoot '.ai-workspace/workspace.toml'),
    (Join-Path $assetRoot '.ai-workspace/versions.lock'),
    (Join-Path $assetRoot '.ai-workspace/templates/workspace.toml'),
    (Join-Path $assetRoot '.ai-workspace/templates/versions.lock')
)) {
    Require-ExactLine -Path $versionMetadata -Expected "product = `"$releaseVersion`""
}
Invoke-Python -Arguments @(
    (Join-Path $repoRoot 'scripts/generate-release-manifest.py'),
    '--asset-root', $assetRoot,
    '--release-version', $releaseVersion,
    '--check'
)
& $nodeCommand (Join-Path $repoRoot 'scripts/validate-json-instance.mjs') `
    (Join-Path $repoRoot 'schemas/release-manifest.schema.json') `
    (Join-Path $assetRoot '.ai-workspace/release-manifest.json') | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$runtimeSkillCount = @(Get-ChildItem -LiteralPath (Join-Path $assetRoot 'skills') -Directory -Force).Count
if ($runtimeSkillCount -ne 9) { Fail "Expected 9 runtime skills, found $runtimeSkillCount." }

Write-Output 'Product structure validation passed.'
