#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    [Console]::Error.WriteLine("ERROR: $Message")
    exit 2
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

function Read-BundleToml {
    param([Parameter(Mandatory = $true)][string]$Path)
    $types = @{
        'bundle.id' = 'string'; 'bundle.version' = 'string'; 'bundle.status' = 'string'; 'bundle.format' = 'string';
        'versions.workspace' = 'string'; 'versions.release_manifest' = 'string'; 'versions.environment_facts' = 'string';
        'versions.project_plugin' = 'string'; 'versions.diagnostic_profile' = 'string'; 'versions.task' = 'string';
        'versions.feedback_report' = 'string'; 'versions.project_plugin_api' = 'string'; 'versions.diagnostic_plugin_api' = 'string';
        'payload.workspace_asset' = 'string'; 'payload.required_entries' = 'array';
        'safety.network_default' = 'string'; 'safety.install_tools' = 'boolean'; 'safety.modify_shell' = 'boolean';
        'safety.overwrite_non_empty' = 'boolean'; 'safety.self_update' = 'boolean'
    }
    $allowedSections = @('bundle', 'versions', 'payload', 'safety')
    $values = @{}
    $entries = New-Object Collections.Generic.List[string]
    $seenEntries = @{}
    $seenSections = @{}
    $section = ''
    $inArray = $false

    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = (Remove-TomlComment -Line $rawLine).Trim()
        if ($line.Length -eq 0) { continue }
        if ($inArray) {
            if ($line -eq ']') { $inArray = $false; continue }
            $item = $line
            if ($item.EndsWith(',')) { $item = $item.Substring(0, $item.Length - 1).Trim() }
            if ($item -notmatch '^"[^"\\]+"$') { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
            $entry = $item.Substring(1, $item.Length - 2)
            if ($seenEntries.ContainsKey($entry)) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
            $seenEntries[$entry] = $true
            $entries.Add($entry)
            continue
        }
        if ($line.StartsWith('[')) {
            if ($line -notmatch '^\[([a-z_]+)\]$') { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
            $section = $Matches[1]
            if ($allowedSections -notcontains $section -or $seenSections.ContainsKey($section)) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
            $seenSections[$section] = $true
            continue
        }
        $separator = $line.IndexOf('=')
        if ($separator -lt 1 -or $section.Length -eq 0) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
        $key = $line.Substring(0, $separator).Trim()
        $rawValue = $line.Substring($separator + 1).Trim()
        $qualified = "$section.$key"
        if (-not $types.ContainsKey($qualified) -or $values.ContainsKey($qualified)) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
        switch ($types[$qualified]) {
            'string' {
                if ($rawValue -notmatch '^"[^"\\]*"$') { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
                $values[$qualified] = $rawValue.Substring(1, $rawValue.Length - 2)
            }
            'boolean' {
                if ($rawValue -eq 'true') { $values[$qualified] = $true }
                elseif ($rawValue -eq 'false') { $values[$qualified] = $false }
                else { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
            }
            'array' {
                if ($rawValue -ne '[') { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
                $values[$qualified] = $true
                $inArray = $true
            }
        }
    }
    if ($inArray -or $entries.Count -eq 0 -or $values.Count -ne $types.Count) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
    foreach ($key in $types.Keys) {
        if (-not $values.ContainsKey($key)) { Fail 'bundle.toml violates the canonical V0.1 metadata contract' }
    }
    return [PSCustomObject]@{ Values = $values; RequiredEntries = $entries.ToArray() }
}

function Require-Value {
    param([hashtable]$Values, [string]$Key, $Expected)
    if (-not $Values.ContainsKey($Key) -or $Values[$Key] -ne $Expected) {
        Fail "bundle.toml $Key does not match the required V0.1 value"
    }
}

function Test-ReparsePoint {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return ((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}

function Test-SafeRelativePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or [IO.Path]::IsPathRooted($Path) -or $Path -match '\s' -or $Path.Contains('//')) { return $false }
    foreach ($segment in $Path.Split('/')) {
        if ($segment.Length -eq 0 -or $segment -eq '.' -or $segment -eq '..') { return $false }
    }
    return $true
}

function Get-RelativeForwardPath {
    param([string]$Root, [string]$Path)
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    return [IO.Path]::GetFullPath($Path).Substring($prefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
}

function Validate-RuntimeSkill {
    param([string]$Name)
    $skillFile = Join-Path $script:AssetDirectory "skills/$Name/SKILL.md"
    $agentFile = Join-Path $script:AssetDirectory "skills/$Name/agents/openai.yaml"
    if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf) -or (Get-Item -LiteralPath $skillFile).Length -eq 0) { Fail "missing runtime Skill: $skillFile" }
    if (-not (Test-Path -LiteralPath $agentFile -PathType Leaf) -or (Get-Item -LiteralPath $agentFile).Length -eq 0) { Fail "missing runtime Skill agent metadata: $agentFile" }
    $lines = @(Get-Content -LiteralPath $skillFile)
    if ($lines.Count -eq 0 -or $lines[0] -cne '---') { Fail "invalid Skill frontmatter start: $skillFile" }
    if ($lines -cnotcontains "name: $Name") { Fail "runtime Skill name does not match directory: $skillFile" }
    if ($null -eq ($lines | Where-Object { $_ -match '^description: .+' } | Select-Object -First 1)) { Fail "runtime Skill description is missing: $skillFile" }
    if ((Get-Content -LiteralPath $skillFile -Raw).Contains('TODO')) { Fail "runtime Skill contains an unresolved template placeholder: $skillFile" }
}

function Validate-ManifestOwnership {
    $ownershipFile = Join-Path $script:AssetDirectory '.ai-workspace/ownership.toml'
    $manifestFile = Join-Path $script:AssetDirectory '.ai-workspace/distribution.manifest'
    if (-not (Test-Path -LiteralPath $ownershipFile -PathType Leaf)) { Fail "missing ownership policy: $ownershipFile" }
    $defaultOwner = $null
    $resolution = $null
    $rules = New-Object Collections.Generic.List[object]
    $pendingPattern = $null
    foreach ($rawLine in Get-Content -LiteralPath $ownershipFile) {
        $line = (Remove-TomlComment -Line $rawLine).Trim()
        if ($line -eq '[[rules]]') { $pendingPattern = $null; continue }
        if ($line -match '^default\s*=\s*"([^"\\]+)"$') { $defaultOwner = $Matches[1]; continue }
        if ($line -match '^resolution\s*=\s*"([^"\\]+)"$') { $resolution = $Matches[1]; continue }
        if ($line -match '^pattern\s*=\s*"([^"\\]+)"$') { $pendingPattern = $Matches[1]; continue }
        if ($line -match '^owner\s*=\s*"([^"\\]+)"$' -and $null -ne $pendingPattern) {
            $rules.Add([PSCustomObject]@{ Pattern = $pendingPattern; Owner = $Matches[1] })
            $pendingPattern = $null
        }
    }
    if ($null -eq $defaultOwner -or $resolution -ne 'first-match' -or $rules.Count -eq 0) { Fail 'ownership.toml violates the V0.1 ownership contract' }
    foreach ($rawEntry in Get-Content -LiteralPath $manifestFile) {
        $entry = $rawEntry
        if ($entry.Length -eq 0 -or $entry.StartsWith('#')) { continue }
        $owner = $defaultOwner
        foreach ($rule in $rules) {
            if ($rule.Pattern.EndsWith('/**')) {
                $root = $rule.Pattern.Substring(0, $rule.Pattern.Length - 3)
                if ($entry -eq $root -or $entry.StartsWith("$root/", [StringComparison]::Ordinal)) { $owner = $rule.Owner; break }
            }
            elseif ($entry -ceq $rule.Pattern) { $owner = $rule.Owner; break }
        }
        if ($owner -ne 'distribution') { Fail "distribution manifest path is not distribution-owned: $entry" }
    }
}

function Validate-Checksums {
    $checksumFile = Join-Path $script:SkillDirectory 'checksums/workspace-v0.1.sha256'
    if (-not (Test-Path -LiteralPath $checksumFile -PathType Leaf) -or (Get-Item -LiteralPath $checksumFile).Length -eq 0) { Fail 'missing workspace checksum manifest' }
    $expected = @{}
    foreach ($line in Get-Content -LiteralPath $checksumFile) {
        if ($line -notmatch '^([0-9A-Fa-f]{64})  (.+)$') { Fail 'malformed workspace checksum manifest' }
        $digest = $Matches[1].ToLowerInvariant()
        $relative = $Matches[2]
        if (-not (Test-SafeRelativePath -Path $relative) -or $expected.ContainsKey($relative)) { Fail 'unsafe or duplicate path in workspace checksum manifest' }
        $expected[$relative] = $digest
    }
    $actualFiles = @(
        Get-ChildItem -LiteralPath $script:AssetDirectory -Recurse -File -Force | ForEach-Object {
            Get-RelativeForwardPath -Root $script:AssetDirectory -Path $_.FullName
        }
    )
    if ($actualFiles.Count -ne $expected.Count) { Fail 'checksum manifest does not cover the exact asset file set' }
    foreach ($relative in $actualFiles) {
        if (-not $expected.ContainsKey($relative)) { Fail 'checksum manifest does not cover the exact asset file set' }
        $nativePath = Join-Path $script:AssetDirectory ($relative.Replace('/', [IO.Path]::DirectorySeparatorChar))
        $digest = (Get-FileHash -LiteralPath $nativePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -cne $expected[$relative]) { Fail "workspace asset checksum mismatch: $relative" }
    }
}

$scriptDirectory = $PSScriptRoot
$skillDirectory = [IO.Path]::GetFullPath((Join-Path $scriptDirectory '..'))
$assetDirectory = Join-Path $skillDirectory 'assets/workspace-v0.1'
$bundleFile = Join-Path $skillDirectory 'bundle.toml'
$script:SkillDirectory = $skillDirectory
$script:AssetDirectory = $assetDirectory

foreach ($requiredFile in @(
    (Join-Path $skillDirectory 'SKILL.md'),
    (Join-Path $skillDirectory 'agents/openai.yaml'),
    $bundleFile,
    (Join-Path $scriptDirectory 'create-workspace.sh'),
    (Join-Path $scriptDirectory 'create-workspace.ps1'),
    (Join-Path $scriptDirectory 'validate-workspace.sh'),
    (Join-Path $scriptDirectory 'validate-workspace.ps1'),
    (Join-Path $scriptDirectory 'plan-repair.sh'),
    (Join-Path $scriptDirectory 'plan-repair.ps1')
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf) -or (Get-Item -LiteralPath $requiredFile).Length -eq 0) { Fail "missing required bundle file: $requiredFile" }
}
if (-not (Test-Path -LiteralPath $assetDirectory -PathType Container)) { Fail "missing asset root: $assetDirectory" }
if ((Get-Content -LiteralPath (Join-Path $skillDirectory 'SKILL.md') -Raw).Contains('TODO')) { Fail 'external Skill contains an unresolved template placeholder' }

$bundle = Read-BundleToml -Path $bundleFile
$expectedValues = @{
    'bundle.id' = 'bootstrap-workcell'; 'bundle.version' = '0.2.0'; 'bundle.status' = 'stable'; 'bundle.format' = 'text-only-skill-bundle';
    'versions.workspace' = '0.1'; 'versions.release_manifest' = '0.1'; 'versions.environment_facts' = '0.1';
    'versions.project_plugin' = '0.1'; 'versions.diagnostic_profile' = '0.1'; 'versions.task' = '0.1';
    'versions.feedback_report' = '0.1'; 'versions.project_plugin_api' = '0.1'; 'versions.diagnostic_plugin_api' = '0.1';
    'payload.workspace_asset' = 'assets/workspace-v0.1'; 'safety.network_default' = 'deny';
    'safety.install_tools' = $false; 'safety.modify_shell' = $false; 'safety.overwrite_non_empty' = $false; 'safety.self_update' = $false
}
foreach ($key in $expectedValues.Keys) { Require-Value -Values $bundle.Values -Key $key -Expected $expectedValues[$key] }
$requiredEntries = @('AI_WORKSPACE.md', 'AGENTS.md', 'LICENSE', '.ai-workspace/workspace.toml', '.ai-workspace/versions.lock', '.ai-workspace/release-manifest.json', '.ai-workspace/distribution.manifest', '.ai-workspace/ownership.toml', 'skills')
foreach ($entry in $requiredEntries) {
    if ($bundle.RequiredEntries -cnotcontains $entry) { Fail "bundle.toml is missing required entry: $entry" }
}

$skillLines = @(Get-Content -LiteralPath (Join-Path $skillDirectory 'SKILL.md'))
if ($skillLines -cnotcontains 'name: bootstrap-workcell') { Fail 'external Skill name is invalid' }
$agentLines = @(Get-Content -LiteralPath (Join-Path $skillDirectory 'agents/openai.yaml'))
if ($agentLines -cnotcontains '  display_name: "Bootstrap Workcell"') { Fail 'external Skill agent metadata is invalid' }

$reparse = Get-ChildItem -LiteralPath $assetDirectory -Recurse -Force | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 } | Select-Object -First 1
if ($null -ne $reparse) { Fail "symbolic links or junctions are not allowed in V0.1 assets: $($reparse.FullName)" }
$cache = Get-ChildItem -LiteralPath $assetDirectory -Recurse -Force | Where-Object {
    $_.Name -eq '__pycache__' -or $_.Name -in @('.DS_Store', '.pytest_cache', '.mypy_cache', '.ruff_cache') -or $_.Extension -in @('.pyc', '.pyo')
} | Select-Object -First 1
if ($null -ne $cache) { Fail "generated cache is not allowed in V0.1 assets: $($cache.FullName)" }

foreach ($runtimeName in @(
    'initialize-workcell', 'inspect-host-environment', 'adapt-project-workspace', 'configure-project-diagnostics',
    'workcell-doctor', 'start-workcell-task', 'upgrade-workcell', 'extract-workcell-feedback', 'localize-workcell'
)) { Validate-RuntimeSkill -Name $runtimeName }

Validate-ManifestOwnership
Validate-Checksums
& (Join-Path $scriptDirectory 'validate-workspace.ps1') -WorkspaceDirectory $assetDirectory | Out-Null
Write-Output "VALID: bundle $skillDirectory"
