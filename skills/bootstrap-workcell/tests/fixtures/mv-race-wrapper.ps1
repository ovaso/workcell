#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)][string]$Source,
    [Parameter(Position = 1, Mandatory = $true)][string]$Destination
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($env:BOOTSTRAP_RACE_MARKER) -or [string]::IsNullOrWhiteSpace($env:BOOTSTRAP_RACE_TARGET)) {
    throw 'BOOTSTRAP_RACE_MARKER and BOOTSTRAP_RACE_TARGET are required.'
}
if (-not (Test-Path -LiteralPath $env:BOOTSTRAP_RACE_MARKER)) {
    New-Item -ItemType File -Path $env:BOOTSTRAP_RACE_MARKER | Out-Null
    New-Item -ItemType Directory -Path $env:BOOTSTRAP_RACE_TARGET | Out-Null
}
Move-Item -LiteralPath $Source -Destination $Destination
