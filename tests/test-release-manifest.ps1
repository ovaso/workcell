#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'StdWorkspace.TestHelpers.psm1') -Force
$env:PYTHONDONTWRITEBYTECODE = '1'
Invoke-Python3 -Arguments @((Join-Path $PSScriptRoot 'test-release-manifest.py'))
