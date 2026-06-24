param(
  [string]$DatabasePath = "",
  [switch]$Backup
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$InitialDatabase = Join-Path $Root "app\data\career_helper_initial.sqlite3"
$DefaultDatabase = Join-Path $Root "app\data\career_helper.sqlite3"
$TargetDatabase = if ($DatabasePath) { $DatabasePath } else { $DefaultDatabase }

if (-not [System.IO.Path]::IsPathRooted($TargetDatabase)) {
  $TargetDatabase = Join-Path $Root $TargetDatabase
}

$InitialDatabase = [System.IO.Path]::GetFullPath($InitialDatabase)
$TargetDatabase = [System.IO.Path]::GetFullPath($TargetDatabase)
$TargetDirectory = Split-Path -Parent $TargetDatabase

if (-not (Test-Path -LiteralPath $InitialDatabase)) {
  throw "Initial database not found: $InitialDatabase"
}

if (-not (Test-Path -LiteralPath $TargetDirectory)) {
  New-Item -ItemType Directory -Path $TargetDirectory | Out-Null
}

if ((Test-Path -LiteralPath $TargetDatabase) -and $Backup) {
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $backup = "$TargetDatabase.bak-$timestamp"
  Copy-Item -LiteralPath $TargetDatabase -Destination $backup -Force
  Write-Host "Backup created: $backup"
}

Copy-Item -LiteralPath $InitialDatabase -Destination $TargetDatabase -Force
Write-Host "Database reset from: $InitialDatabase"
Write-Host "Database written to: $TargetDatabase"
