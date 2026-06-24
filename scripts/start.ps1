$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$Dist = Join-Path $Frontend "dist"

. (Join-Path $PSScriptRoot "lib\ports.ps1")

$env:CAREER_ENABLE_REAL_AI = if ($env:CAREER_ENABLE_REAL_AI) { $env:CAREER_ENABLE_REAL_AI } else { "false" }

if ($env:CAREER_ENABLE_REAL_AI -eq "true") {
  & (Join-Path $PSScriptRoot "bootstrap.ps1") -IncludeAi
} else {
  & (Join-Path $PSScriptRoot "bootstrap.ps1")
}

if (-not (Test-Path $Dist)) {
  Push-Location $Frontend
  try {
    conda run -n career-helper-app npm.cmd run build
  } finally {
    Pop-Location
  }
}

if (-not (Assert-BackendPortAvailable -Port 8000)) {
  return
}

Write-Host "Starting AI Career Helper at http://127.0.0.1:8000/"
conda run -n career-helper-app uvicorn app.main:app --host 127.0.0.1 --port 8000
