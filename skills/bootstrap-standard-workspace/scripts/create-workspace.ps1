#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)][string]$TargetDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail {
    param([string]$Message, [int]$Code = 2)
    [Console]::Error.WriteLine("ERROR: $Message")
    exit $Code
}

function Test-ReparsePoint {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return ((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}

function Copy-DirectoryContent {
    param([string]$Source, [string]$Destination)
    New-Item -ItemType Directory -Path $Destination | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

if ([string]::IsNullOrWhiteSpace($TargetDirectory) -or $TargetDirectory -in @('.', '..')) {
    Fail "target must be an explicit workspace directory, not '$TargetDirectory'."
}

$scriptDirectory = $PSScriptRoot
$skillDirectory = [IO.Path]::GetFullPath((Join-Path $scriptDirectory '..'))
$assetDirectory = Join-Path $skillDirectory 'assets/workspace-v0.1'
& (Join-Path $scriptDirectory 'validate-bundle.ps1') | Out-Null

$fullTarget = [IO.Path]::GetFullPath($TargetDirectory).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
if ($fullTarget -eq [IO.Path]::GetPathRoot($fullTarget).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)) {
    Fail "target must not be a filesystem root: $fullTarget"
}
$targetName = Split-Path -Leaf $fullTarget
$targetParent = Split-Path -Parent $fullTarget
if ([string]::IsNullOrWhiteSpace($targetName)) { Fail "target basename is unsafe: '$targetName'." }
New-Item -ItemType Directory -Path $targetParent -Force | Out-Null

if (Test-ReparsePoint -Path $fullTarget) { Fail "target must not be a symbolic link or junction: $fullTarget" 1 }
$targetPreexisted = Test-Path -LiteralPath $fullTarget
if ($targetPreexisted) {
    if (-not (Test-Path -LiteralPath $fullTarget -PathType Container)) { Fail "target exists and is not a directory: $fullTarget" 1 }
    if ($null -ne (Get-ChildItem -LiteralPath $fullTarget -Force | Select-Object -First 1)) { Fail "refusing to overwrite non-empty target: $fullTarget" 1 }
}

$stageName = ".$targetName.bootstrap.$PID.$([Guid]::NewGuid().ToString('N'))"
$stageDirectory = Join-Path $targetParent $stageName
if (Test-Path -LiteralPath $stageDirectory) { Fail "staging path already exists: $stageDirectory" }
$markerName = '.bootstrap-install-token'
$markerValue = [Guid]::NewGuid().ToString('N')

try {
    Copy-DirectoryContent -Source $assetDirectory -Destination $stageDirectory
    & (Join-Path $scriptDirectory 'validate-workspace.ps1') -WorkspaceDirectory $stageDirectory | Out-Null
    $utf8NoBom = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $stageDirectory $markerName), $markerValue, $utf8NoBom)

    if ($targetPreexisted) {
        if ($null -ne (Get-ChildItem -LiteralPath $fullTarget -Force | Select-Object -First 1)) { Fail "target changed after the emptiness check: $fullTarget" 1 }
        Remove-Item -LiteralPath $fullTarget -Force
    }
    if (Test-Path -LiteralPath $fullTarget) { Fail "target appeared during staged installation: $fullTarget" 1 }

    try { Move-Item -LiteralPath $stageDirectory -Destination $fullTarget -ErrorAction Stop }
    catch {
        if ($targetPreexisted -and -not (Test-Path -LiteralPath $fullTarget)) { New-Item -ItemType Directory -Path $fullTarget | Out-Null }
        Fail "failed to install staged workspace at: $fullTarget"
    }

    $installedMarker = Join-Path $fullTarget $markerName
    if (-not (Test-Path -LiteralPath $installedMarker -PathType Leaf) -or (Get-Content -LiteralPath $installedMarker -Raw) -ne $markerValue) {
        $nestedStage = Join-Path $fullTarget $stageName
        if (Test-Path -LiteralPath (Join-Path $nestedStage $markerName)) {
            Move-Item -LiteralPath $nestedStage -Destination $stageDirectory -ErrorAction SilentlyContinue
        }
        Fail "target raced with installation; refusing successful completion: $fullTarget" 1
    }
    Remove-Item -LiteralPath $installedMarker -Force
    $stageDirectory = $null
    Write-Output "CREATED: $fullTarget"
}
finally {
    if ($null -ne $stageDirectory -and (Test-Path -LiteralPath $stageDirectory)) {
        Remove-Item -LiteralPath $stageDirectory -Recurse -Force
    }
}
