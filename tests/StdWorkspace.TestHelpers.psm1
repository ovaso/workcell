Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-PythonInvocation {
    foreach ($candidate in @('python3', 'python')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) { return @{ Command = $command.Source; Prefix = @() } }
    }
    $launcher = Get-Command 'py' -ErrorAction SilentlyContinue
    if ($null -ne $launcher) { return @{ Command = $launcher.Source; Prefix = @('-3') } }
    throw 'Python 3.11 or newer is required.'
}

function Invoke-Python3 {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $invocation = Get-PythonInvocation
    $command = $invocation.Command
    $allArguments = @($invocation.Prefix) + $Arguments
    & $command @allArguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE." }
}

function Invoke-Node {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($null -eq $node) { throw 'Node.js is required.' }
    $command = $node.Source
    & $command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Node.js command failed with exit code $LASTEXITCODE." }
}

function Get-PowerShellExecutable {
    return (Get-Process -Id $PID).Path
}

function New-TestDirectory {
    param([Parameter(Mandatory = $true)][string]$Prefix)
    $path = Join-Path ([IO.Path]::GetTempPath()) ($Prefix + '.' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $path | Out-Null
    return $path
}

function Write-Utf8NoBom {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Content)
    $encoding = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Get-RelativeForwardPath {
    param([Parameter(Mandatory = $true)][string]$Root, [Parameter(Mandatory = $true)][string]$Path)
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    return [IO.Path]::GetFullPath($Path).Substring($prefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
}

function Get-TreeSnapshot {
    param([Parameter(Mandatory = $true)][string]$Root)
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

function Assert-DirectoriesEqual {
    param([string]$Left, [string]$Right)
    $leftSnapshot = @(Get-TreeSnapshot -Root $Left)
    $rightSnapshot = @(Get-TreeSnapshot -Root $Right)
    if ($leftSnapshot.Count -ne $rightSnapshot.Count) { throw "Directory trees differ: $Left and $Right" }
    for ($index = 0; $index -lt $leftSnapshot.Count; $index++) {
        if ($leftSnapshot[$index] -cne $rightSnapshot[$index]) { throw "Directory trees differ: $Left and $Right" }
    }
}

function Assert-FilesEqual {
    param([string]$Left, [string]$Right)
    if ((Get-FileHash -LiteralPath $Left -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $Right -Algorithm SHA256).Hash) {
        throw "Files differ: $Left and $Right"
    }
}

function Copy-DirectoryContent {
    param([string]$Source, [string]$Destination)
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

Export-ModuleMember -Function Get-PythonInvocation, Invoke-Python3, Invoke-Node, Get-PowerShellExecutable, New-TestDirectory, Write-Utf8NoBom, Get-RelativeForwardPath, Get-TreeSnapshot, Assert-DirectoriesEqual, Assert-FilesEqual, Copy-DirectoryContent
