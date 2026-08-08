#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$testDirectory = $PSScriptRoot
$skillDirectory = [IO.Path]::GetFullPath((Join-Path $testDirectory '..'))
$scriptDirectory = Join-Path $skillDirectory 'scripts'
$assetDirectory = Join-Path $skillDirectory 'assets/workspace-v0.1'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('bootstrap-standard-workspace.' + [Guid]::NewGuid().ToString('N'))
$powerShell = (Get-Process -Id $PID).Path
$utf8NoBom = New-Object Text.UTF8Encoding($false)
New-Item -ItemType Directory -Path $testRoot | Out-Null

function Copy-DirectoryContent {
    param([string]$Source, [string]$Destination)
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

function Invoke-Script {
    param([string]$Path, [string[]]$Arguments = @())
    $output = @(& $powerShell -NoProfile -ExecutionPolicy Bypass -File $Path @Arguments 2>&1)
    return [PSCustomObject]@{ ExitCode = $LASTEXITCODE; Output = ($output -join "`n") }
}

function Assert-Failed {
    param([object]$Result, [string]$Message)
    if ($Result.ExitCode -eq 0) { throw "TEST FAILED: $Message" }
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
    return ,$array
}

function Assert-DirectoriesEqual {
    param([string]$Left, [string]$Right)
    $leftSnapshot = @(Get-TreeSnapshot -Root $Left)
    $rightSnapshot = @(Get-TreeSnapshot -Root $Right)
    if (($leftSnapshot -join "`n") -cne ($rightSnapshot -join "`n")) { throw "TEST FAILED: directory trees differ: $Left and $Right" }
}

try {
    $bundleResult = Invoke-Script -Path (Join-Path $scriptDirectory 'validate-bundle.ps1')
    if ($bundleResult.ExitCode -ne 0) { throw "TEST FAILED: valid bundle was rejected: $($bundleResult.Output)" }

    $metadataSkill = Join-Path $testRoot 'bundle-metadata-skill'
    Copy-DirectoryContent -Source $skillDirectory -Destination $metadataSkill
    $bundlePath = Join-Path $metadataSkill 'bundle.toml'
    $bundleOriginal = Get-Content -LiteralPath $bundlePath -Raw

    [IO.File]::WriteAllText($bundlePath, ($bundleOriginal -replace '(?m)^\[bundle\]$', '[wrong-section]'), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $metadataSkill 'scripts/validate-bundle.ps1')) -Message 'bundle validator accepted an invalid section'

    [IO.File]::WriteAllText($bundlePath, ($bundleOriginal -replace '(?m)^\[versions\]$', "id = `"bootstrap-standard-workspace`"`n[versions]"), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $metadataSkill 'scripts/validate-bundle.ps1')) -Message 'bundle validator accepted a duplicate key'

    [IO.File]::WriteAllText($bundlePath, ($bundleOriginal -replace '(?m)^install_tools = false$', 'install_tools = "false"'), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $metadataSkill 'scripts/validate-bundle.ps1')) -Message 'bundle validator accepted a boolean encoded as a string'

    [IO.File]::WriteAllText($bundlePath, ($bundleOriginal -replace '(?ms)^required_entries = \[.*?^\]\r?\n', ''), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $metadataSkill 'scripts/validate-bundle.ps1')) -Message 'bundle validator accepted a missing required_entries array'

    $tamperedSkill = Join-Path $testRoot 'tampered-skill'
    Copy-DirectoryContent -Source $skillDirectory -Destination $tamperedSkill
    [IO.File]::AppendAllText((Join-Path $tamperedSkill 'assets/workspace-v0.1/AI_WORKSPACE.md'), "checksum-tamper-test`n", $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $tamperedSkill 'scripts/validate-bundle.ps1')) -Message 'bundle validator accepted a checksum mismatch'

    $createdWorkspace = Join-Path $testRoot 'created-workspace'
    $createResult = Invoke-Script -Path (Join-Path $scriptDirectory 'create-workspace.ps1') -Arguments @($createdWorkspace)
    if ($createResult.ExitCode -ne 0 -or $createResult.Output -notmatch '(?m)^CREATED:') { throw "TEST FAILED: create script failed: $($createResult.Output)" }
    $validateResult = Invoke-Script -Path (Join-Path $scriptDirectory 'validate-workspace.ps1') -Arguments @($createdWorkspace)
    if ($validateResult.ExitCode -ne 0) { throw "TEST FAILED: created workspace was rejected: $($validateResult.Output)" }
    Assert-DirectoriesEqual -Left $assetDirectory -Right $createdWorkspace

    $invalidWorkspace = Join-Path $testRoot 'invalid-metadata-workspace'
    Copy-DirectoryContent -Source $createdWorkspace -Destination $invalidWorkspace
    $workspaceFile = Join-Path $invalidWorkspace '.ai-workspace/workspace.toml'
    $workspaceOriginal = Get-Content -LiteralPath $workspaceFile -Raw
    [IO.File]::WriteAllText($workspaceFile, ($workspaceOriginal -replace '(?m)^\[workspace\]$', '[wrong-section]'), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $scriptDirectory 'validate-workspace.ps1') -Arguments @('-MetadataOnly', $invalidWorkspace)) -Message 'workspace validator accepted an invalid section'

    [IO.File]::WriteAllText($workspaceFile, ($workspaceOriginal -replace '(?m)^overwrite_non_empty = false$', 'overwrite_non_empty = "false"'), $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $scriptDirectory 'validate-workspace.ps1') -Arguments @('-MetadataOnly', $invalidWorkspace)) -Message 'workspace validator accepted a boolean encoded as a string'

    $existingEmpty = Join-Path $testRoot 'existing-empty-workspace'
    New-Item -ItemType Directory -Path $existingEmpty | Out-Null
    $emptyCreate = Invoke-Script -Path (Join-Path $scriptDirectory 'create-workspace.ps1') -Arguments @($existingEmpty)
    if ($emptyCreate.ExitCode -ne 0) { throw 'TEST FAILED: create script rejected an existing empty target' }

    $nonempty = Join-Path $testRoot 'nonempty-workspace'
    New-Item -ItemType Directory -Path $nonempty | Out-Null
    [IO.File]::WriteAllText((Join-Path $nonempty 'user-file.txt'), 'preserve me', $utf8NoBom)
    Assert-Failed -Result (Invoke-Script -Path (Join-Path $scriptDirectory 'create-workspace.ps1') -Arguments @($nonempty)) -Message 'create script accepted a non-empty target'
    if ((Get-Content -LiteralPath (Join-Path $nonempty 'user-file.txt') -Raw) -ne 'preserve me') { throw 'TEST FAILED: non-empty target was modified' }

    $managedFile = $null
    foreach ($rawPath in Get-Content -LiteralPath (Join-Path $createdWorkspace '.ai-workspace/distribution.manifest')) {
        $candidate = $rawPath.Trim()
        if ($candidate.Length -eq 0 -or $candidate.StartsWith('#')) { continue }
        $candidatePath = Join-Path $createdWorkspace ($candidate.Replace('/', [IO.Path]::DirectorySeparatorChar))
        if (Test-Path -LiteralPath $candidatePath -PathType Leaf) { $managedFile = $candidate; break }
    }
    if ($null -eq $managedFile) { throw 'TEST FAILED: manifest contains no managed regular file' }
    $managedWorkspacePath = Join-Path $createdWorkspace ($managedFile.Replace('/', [IO.Path]::DirectorySeparatorChar))
    [IO.File]::AppendAllText($managedWorkspacePath, "repair-plan-test`n", $utf8NoBom)
    $driftResult = Invoke-Script -Path (Join-Path $scriptDirectory 'validate-workspace.ps1') -Arguments @($createdWorkspace)
    if ($driftResult.ExitCode -ne 1) { throw 'TEST FAILED: workspace validator did not use drift exit code 1' }
    $repairResult = Invoke-Script -Path (Join-Path $scriptDirectory 'plan-repair.ps1') -Arguments @($createdWorkspace)
    if ($repairResult.ExitCode -ne 1 -or $repairResult.Output -notmatch "(?m)^MODIFIED`t$([regex]::Escape($managedFile))$") { throw 'TEST FAILED: repair planner did not report the modified managed file' }

    Copy-Item -LiteralPath (Join-Path $assetDirectory ($managedFile.Replace('/', [IO.Path]::DirectorySeparatorChar))) -Destination $managedWorkspacePath -Force
    [IO.File]::AppendAllText((Join-Path $createdWorkspace '.ai-workspace/distribution.manifest'), "# manifest drift`n", $utf8NoBom)
    $manifestRepair = Invoke-Script -Path (Join-Path $scriptDirectory 'plan-repair.ps1') -Arguments @($createdWorkspace)
    if ($manifestRepair.ExitCode -ne 1 -or $manifestRepair.Output -notmatch '(?m)^MODIFIED\t\.ai-workspace/distribution\.manifest$') { throw 'TEST FAILED: repair planner trusted a modified workspace manifest' }

    Write-Output 'TEST PASSED: metadata attacks, containment, integrity, create, validate, and repair planning'
}
finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force }
}
