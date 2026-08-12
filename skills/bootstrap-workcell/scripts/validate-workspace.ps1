#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)][string]$WorkspaceDirectory,
    [switch]$MetadataOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    [Console]::Error.WriteLine("ERROR: $Message")
    exit 2
}

function Drift {
    param([Parameter(Mandatory = $true)][string]$Message)
    [Console]::Error.WriteLine("DRIFT: $Message")
    exit 1
}

function Remove-TomlComment {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Line)
    $builder = New-Object Text.StringBuilder
    $quoted = $false
    $escaped = $false
    foreach ($character in $Line.ToCharArray()) {
        if ($quoted) {
            [void]$builder.Append($character)
            if ($escaped) { $escaped = $false }
            elseif ($character -eq '\') { $escaped = $true }
            elseif ($character -eq '"') { $quoted = $false }
        }
        elseif ($character -eq '#') { break }
        else {
            [void]$builder.Append($character)
            if ($character -eq '"') { $quoted = $true }
        }
    }
    return $builder.ToString()
}

function Read-MetadataToml {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('workspace', 'versions')][string]$Profile
    )

    $types = @{}
    if ($Profile -eq 'workspace') {
        foreach ($key in @('id', 'name', 'status', 'managed_by', 'created_at', 'updated_at')) { $types["workspace.$key"] = 'string' }
        foreach ($key in @('product', 'workspace_schema', 'release_manifest_schema', 'environment_facts_schema', 'project_plugin_schema', 'diagnostic_profile_schema', 'task_schema', 'feedback_report_schema')) { $types["versions.$key"] = 'string' }
        foreach ($key in @('remote_operations_default', 'bootstrap_network')) { $types["safety.$key"] = 'string' }
        $types['safety.overwrite_non_empty'] = 'boolean'
        $allowedSections = @('workspace', 'versions', 'paths', 'safety')
    }
    else {
        foreach ($key in @('product', 'workspace_schema', 'release_manifest_schema', 'environment_facts_schema', 'project_plugin_schema', 'diagnostic_profile_schema', 'task_schema', 'feedback_report_schema', 'project_plugin_api', 'diagnostic_plugin_api')) { $types["versions.$key"] = 'string' }
        foreach ($key in @('channel', 'source')) { $types["release.$key"] = 'string' }
        $types['release.self_update'] = 'boolean'
        $allowedSections = @('versions', 'release')
    }

    $values = @{}
    $seenSections = @{}
    $section = ''
    $lineNumber = 0
    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $lineNumber++
        $line = (Remove-TomlComment -Line $rawLine).Trim()
        if ($line.Length -eq 0) { continue }
        if ($line.StartsWith('[')) {
            if ($line -notmatch '^\[([a-z0-9_.-]+)\]$') { Fail "invalid or non-canonical TOML metadata: $Path" }
            $section = $Matches[1]
            if ($allowedSections -notcontains $section -or $seenSections.ContainsKey($section)) { Fail "invalid or non-canonical TOML metadata: $Path" }
            $seenSections[$section] = $true
            continue
        }
        $separator = $line.IndexOf('=')
        if ($separator -lt 1 -or $section.Length -eq 0) { Fail "invalid or non-canonical TOML metadata: $Path" }
        $key = $line.Substring(0, $separator).Trim()
        $rawValue = $line.Substring($separator + 1).Trim()
        $qualified = "$section.$key"
        $valueType = $null
        if ($types.ContainsKey($qualified)) { $valueType = $types[$qualified] }
        elseif ($Profile -eq 'workspace' -and $section -eq 'paths' -and $key -match '^[a-z0-9_.-]+$') { $valueType = 'string' }
        if ($null -eq $valueType -or $values.ContainsKey($qualified)) { Fail "invalid or non-canonical TOML metadata: $Path" }
        if ($valueType -eq 'string') {
            if ($rawValue -notmatch '^"[^"\\]*"$') { Fail "invalid or non-canonical TOML metadata: $Path" }
            $values[$qualified] = $rawValue.Substring(1, $rawValue.Length - 2)
        }
        elseif ($rawValue -eq 'true') { $values[$qualified] = $true }
        elseif ($rawValue -eq 'false') { $values[$qualified] = $false }
        else { Fail "invalid or non-canonical TOML metadata: $Path" }
    }
    return $values
}

function Require-TomlValue {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Values,
        [Parameter(Mandatory = $true)][string]$QualifiedKey,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Source
    )
    if (-not $Values.ContainsKey($QualifiedKey) -or $Values[$QualifiedKey] -ne $Expected) {
        $actual = '<missing>'
        if ($Values.ContainsKey($QualifiedKey)) { $actual = [string]$Values[$QualifiedKey] }
        Fail "$Source $QualifiedKey expected '$Expected', got '$actual'"
    }
}

function Test-ReparsePoint {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}

function Test-SafeManifestPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ($Path.Length -eq 0 -or $Path.StartsWith('#')) { return $false }
    if ([IO.Path]::IsPathRooted($Path) -or $Path -match '\s' -or $Path.Contains('//')) { Fail "unsafe distribution manifest path: '$Path'" }
    foreach ($segment in $Path.Split('/')) {
        if ($segment.Length -eq 0 -or $segment -eq '.' -or $segment -eq '..') { Fail "unsafe distribution manifest path: '$Path'" }
    }
    return $true
}

function Test-PathContainsReparsePoint {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )
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
    param([Parameter(Mandatory = $true)][string]$Root)
    $entries = New-Object Collections.Generic.List[string]
    foreach ($item in Get-ChildItem -LiteralPath $Root -Recurse -Force) {
        $relative = Get-RelativeForwardPath -Root $Root -Path $item.FullName
        if ($item.PSIsContainer) { $entries.Add("D:$relative") }
        else {
            $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            $entries.Add("F:$relative`:$hash")
        }
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

if (-not (Test-Path -LiteralPath $WorkspaceDirectory -PathType Container)) { Fail "workspace directory does not exist: $WorkspaceDirectory" }
if (Test-ReparsePoint -Path $WorkspaceDirectory) { Fail "workspace directory must not be a symbolic link or junction: $WorkspaceDirectory" }
$workspaceRoot = (Get-Item -LiteralPath $WorkspaceDirectory -Force).FullName

$metadataDirectory = Join-Path $workspaceRoot '.ai-workspace'
if (Test-ReparsePoint -Path $metadataDirectory) { Fail 'required directory must not be a symbolic link or junction: .ai-workspace' }
if (-not (Test-Path -LiteralPath $metadataDirectory -PathType Container)) { Fail 'missing required directory: .ai-workspace' }

if (-not $MetadataOnly) {
    foreach ($requiredDirectory in @('skills', 'environment', 'project', 'mirror', 'remotes', 'requirements', 'workspaces', 'diagnostics', 'tools', 'knowledge', 'docs', 'memory', 'feedback', 'locales')) {
        $path = Join-Path $workspaceRoot $requiredDirectory
        if (Test-ReparsePoint -Path $path) { Fail "required directory must not be a symbolic link or junction: $requiredDirectory" }
        if (-not (Test-Path -LiteralPath $path -PathType Container)) { Fail "missing required directory: $requiredDirectory" }
    }
    foreach ($entry in @('AI_WORKSPACE.md', '.ai-workspace/release-manifest.json', '.ai-workspace/distribution.manifest')) {
        if (Test-PathContainsReparsePoint -Root $workspaceRoot -RelativePath $entry) { Drift "symbolic link or junction found in distribution entry: $entry" }
        $path = Join-Path $workspaceRoot ($entry.Replace('/', [IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) { Drift "missing distribution entry file: $entry" }
    }
}

foreach ($file in @('.ai-workspace/workspace.toml', '.ai-workspace/versions.lock')) {
    if (Test-PathContainsReparsePoint -Root $workspaceRoot -RelativePath $file) { Fail "symbolic link or junction found in required workspace file: $file" }
    $path = Join-Path $workspaceRoot ($file.Replace('/', [IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) { Fail "missing required workspace file: $file" }
}
if (-not $MetadataOnly) {
    if (Test-PathContainsReparsePoint -Root $workspaceRoot -RelativePath 'AGENTS.md') { Fail 'symbolic link or junction found in required workspace file: AGENTS.md' }
    if (-not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'AGENTS.md') -PathType Leaf)) { Fail 'missing required workspace file: AGENTS.md' }
}

$workspaceFile = Join-Path $metadataDirectory 'workspace.toml'
$versionsFile = Join-Path $metadataDirectory 'versions.lock'
$workspaceValues = Read-MetadataToml -Path $workspaceFile -Profile workspace
$versionValues = Read-MetadataToml -Path $versionsFile -Profile versions

foreach ($key in @('workspace.id', 'workspace.name')) {
    if (-not $workspaceValues.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$workspaceValues[$key])) { Fail "$key is missing" }
}
Require-TomlValue -Values $workspaceValues -QualifiedKey 'workspace.managed_by' -Expected 'workcell' -Source $workspaceFile
$workspaceId = [string]$workspaceValues['workspace.id']
if ($workspaceId -notmatch '^[a-z0-9][a-z0-9._-]{1,63}$') { Fail "workspace id is invalid: $workspaceId" }
$allowedStatuses = @('CREATED', 'ENVIRONMENT_INITIALIZED', 'PROJECT_ATTACHED', 'PROJECT_ADAPTED', 'DIAGNOSTICS_CONFIGURED', 'READY', 'DEGRADED', 'PAUSED', 'ARCHIVED')
if (-not $workspaceValues.ContainsKey('workspace.status') -or $allowedStatuses -notcontains $workspaceValues['workspace.status']) { Fail 'unsupported or missing workspace status' }

$versions = @{
    product = '0.3.0'; workspace_schema = '0.1'; release_manifest_schema = '0.1'; environment_facts_schema = '0.1';
    project_plugin_schema = '0.1'; diagnostic_profile_schema = '0.1'; task_schema = '0.1'; feedback_report_schema = '0.1'
}
foreach ($key in $versions.Keys) {
    Require-TomlValue -Values $workspaceValues -QualifiedKey "versions.$key" -Expected $versions[$key] -Source $workspaceFile
    Require-TomlValue -Values $versionValues -QualifiedKey "versions.$key" -Expected $versions[$key] -Source $versionsFile
}
foreach ($key in @('environment', 'project', 'requirements', 'workspaces', 'skills', 'feedback', 'locales')) {
    Require-TomlValue -Values $workspaceValues -QualifiedKey "paths.$key" -Expected $key -Source $workspaceFile
}
Require-TomlValue -Values $workspaceValues -QualifiedKey 'safety.remote_operations_default' -Expected 'deny' -Source $workspaceFile
Require-TomlValue -Values $workspaceValues -QualifiedKey 'safety.bootstrap_network' -Expected 'deny' -Source $workspaceFile
Require-TomlValue -Values $workspaceValues -QualifiedKey 'safety.overwrite_non_empty' -Expected $false -Source $workspaceFile
Require-TomlValue -Values $versionValues -QualifiedKey 'versions.project_plugin_api' -Expected '0.1' -Source $versionsFile
Require-TomlValue -Values $versionValues -QualifiedKey 'versions.diagnostic_plugin_api' -Expected '0.1' -Source $versionsFile
Require-TomlValue -Values $versionValues -QualifiedKey 'release.self_update' -Expected $false -Source $versionsFile

if ($MetadataOnly) {
    Write-Output "VALID: workspace metadata $workspaceRoot"
    exit 0
}

$bundleManifest = Join-Path $assetDirectory '.ai-workspace/distribution.manifest'
$workspaceManifest = Join-Path $workspaceRoot '.ai-workspace/distribution.manifest'
if (-not (Test-Path -LiteralPath $bundleManifest -PathType Leaf)) { Fail 'bundle distribution manifest is missing' }
if (-not (Test-Path -LiteralPath $workspaceManifest -PathType Leaf)) { Drift 'workspace distribution manifest is missing' }
if (-not (Test-FilesEqual -Left $bundleManifest -Right $workspaceManifest)) { Drift 'workspace distribution manifest differs from the bundle' }

$seenManifestPaths = @{}
foreach ($rawPath in Get-Content -LiteralPath $bundleManifest) {
    $managedPath = $rawPath
    if (-not (Test-SafeManifestPath -Path $managedPath)) { continue }
    if ($seenManifestPaths.ContainsKey($managedPath)) { Fail "duplicate distribution manifest path: $managedPath" }
    $seenManifestPaths[$managedPath] = $true
    $nativeRelative = $managedPath.Replace('/', [IO.Path]::DirectorySeparatorChar)
    $sourcePath = Join-Path $assetDirectory $nativeRelative
    $installedPath = Join-Path $workspaceRoot $nativeRelative
    if ((Test-PathContainsReparsePoint -Root $assetDirectory -RelativePath $managedPath) -or (Test-PathContainsReparsePoint -Root $workspaceRoot -RelativePath $managedPath)) {
        Drift "symbolic link or junction found in distribution path: $managedPath"
    }
    if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
        if (-not (Test-Path -LiteralPath $installedPath -PathType Leaf)) { Drift "missing distribution file: $managedPath" }
        if (-not (Test-FilesEqual -Left $sourcePath -Right $installedPath)) { Drift "modified distribution file: $managedPath" }
    }
    elseif (Test-Path -LiteralPath $sourcePath -PathType Container) {
        if (-not (Test-Path -LiteralPath $installedPath -PathType Container)) { Drift "missing distribution directory: $managedPath" }
        if (-not (Test-DirectoriesEqual -Left $sourcePath -Right $installedPath)) { Drift "modified distribution directory: $managedPath" }
    }
    else { Fail "distribution manifest references missing bundle path: $managedPath" }
}

Write-Output "VALID: workspace $workspaceRoot"
