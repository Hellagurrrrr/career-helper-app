$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "lib\ports.ps1")

$ports = @(8000, 5173)

foreach ($port in $ports) {
  $owner = Get-ListeningProcess -Port $port
  if (-not $owner) {
    Write-Host "Port $port is not in use."
    continue
  }

  Write-Host "Stopping PID $($owner.Id) ($($owner.ProcessName)) on port $port..."
  Stop-Process -Id $owner.Id -Force
}
