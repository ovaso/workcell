#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)][string]$WorkspaceDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail {
    param([string]$Message)
    [Console]::Error.WriteLine("ERROR: $Message")
    exit 2
}

function Test-ReparsePoint {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return ((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}

function Test-SafeManifestPath {
    param([string]$Path)
    if ($Path.Length -eq 0 -or $Path.StartsWith('#')) { return $false }
    if ([IO.Path]::IsPathRooted($Path) -or $Path -match '\s' -or $Path.Contains('//')) { Fail "unsafe distribution manifest path: '$Path'" }
    foreach ($segment in $Path.Split('/')) {
        if ($segment.Length -eq 0 -or $segment -eq '.' -or $segment -eq '..') { Fail "unsafe distribution manifest path: '$Path'" }
    }
    return $true
}

function Test-PathContainsReparsePoint {
    param([string]$Root, [string]$RelativePath)
    $current = $Root
    foreach ($segment in $RelativePath.Split('/')) {
        $current = Join-Path $current $segment
        if (Test-ReparsePoint -Path $current) { return $true }
    }
    return $false
}

function Get-RelativeForwardPath {
    param([string]$Root, [string]$Path)
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    return [IO.Path]::GetFullPath($Path).Substring($prefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
}

function Get-TreeSnapshot {
    param([string]$Root)
    $entries = New-Object Collections.Generic.List[string]
    foreach ($item in Get-ChildItem -LiteralPath $Root -Recurse -Force) {
        $relative = Get-RelativeForwardPath -Root $Root -Path $item.FullName
        if ($item.PSIsContainer) { $entries.Add("D:$relative") }
        else { $entries.Add("F:$relative`:$((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash)") }
    }
    $array = $entries.ToArray()
    [Array]::Sort($array, [StringComparer]::Ordinal)
    return $array
}

function Test-DirectoriesEqual {
    param([string]$Left, [string]$Right)
    $leftSnapshot = @(Get-TreeSnapshot -Root $Left)
    $rightSnapshot = @(Get-TreeSnapshot -Root $Right)
    if ($leftSnapshot.Count -ne $rightSnapshot.Count) { return $false }
    for ($index = 0; $index -lt $leftSnapshot.Count; $index++) {
        if ($leftSnapshot[$index] -cne $rightSnapshot[$index]) { return $false }
    }
    return $true
}

function Test-FilesEqual {
    param([string]$Left, [string]$Right)
    return (Get-FileHash -LiteralPath $Left -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $Right -Algorithm SHA256).Hash
}

$scriptDirectory = $PSScriptRoot
$skillDirectory = [IO.Path]::GetFullPath((Join-Path $scriptDirectory '..'))
$assetDirectory = Join-Path $skillDirectory 'assets/workspace-v0.1'

& (Join-Path $scriptDirectory 'validate-bundle.ps1') | Out-Null
if (-not (Test-Path -LiteralPath $WorkspaceDirectory -PathType Container)) { Fail "workspace directory does not exist: $WorkspaceDirectory" }
if (Test-ReparsePoint -Path $WorkspaceDirectory) { Fail "workspace directory must not be a symbolic link or junction: $WorkspaceDirectory" }
$workspaceRoot = (Get-Item -LiteralPath $WorkspaceDirectory -Force).FullName
& (Join-Path $scriptDirectory 'validate-workspace.ps1') -WorkspaceDirectory $workspaceRoot -MetadataOnly | Out-Null

$manifest = Join-Path $assetDirectory '.ai-workspace/distribution.manifest'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or (Get-Item -LiteralPath $manifest).Length -eq 0) { Fail "bundle distribution manifest is missing: $manifest" }
$seen = @{}
$driftFound = $false
foreach ($rawPath in Get-Content -LiteralPath $manifest) {
    $managedPath = $rawPath
    if (-not (Test-SafeManifestPath -Path $managedPath)) { continue }
    if ($seen.ContainsKey($managedPath)) { Fail "duplicate distribution manifest path: $managedPath" }
    $seen[$managedPath] = $true
    $relative = $managedPath.Replace('/', [IO.Path]::DirectorySeparatorChar)
    $sourcePath = Join-Path $assetDirectory $relative
    $installedPath = Join-Path $workspaceRoot $relative
    $status = 'OK'
    if ((Test-PathContainsReparsePoint -Root $assetDirectory -RelativePath $managedPath) -or (Test-PathContainsReparsePoint -Root $workspaceRoot -RelativePath $managedPath)) { $status = 'TYPE_MISMATCH' }
    elseif (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
        if (-not (Test-Path -LiteralPath $installedPath)) { $status = 'MISSING' }
        elseif (-not (Test-Path -LiteralPath $installedPath -PathType Leaf)) { $status = 'TYPE_MISMATCH' }
        elseif (-not (Test-FilesEqual -Left $sourcePath -Right $installedPath)) { $status = 'MODIFIED' }
    }
    elseif (Test-Path -LiteralPath $sourcePath -PathType Container) {
        if (-not (Test-Path -LiteralPath $installedPath)) { $status = 'MISSING' }
        elseif (-not (Test-Path -LiteralPath $installedPath -PathType Container)) { $status = 'TYPE_MISMATCH' }
        elseif (-not (Test-DirectoriesEqual -Left $sourcePath -Right $installedPath)) { $status = 'MODIFIED' }
    }
    else { $status = 'BUNDLE_MISSING' }
    Write-Output "$status`t$managedPath"
    if ($status -ne 'OK') { $driftFound = $true }
}

if ($driftFound) { exit 1 }
exit 0
