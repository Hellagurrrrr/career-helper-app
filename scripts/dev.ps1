$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$Runtime = Join-Path $Root ".cache\runtime"
$BackendPidFile = Join-Path $Runtime "backend.pid"

. (Join-Path $PSScriptRoot "lib\ports.ps1")

$env:CAREER_ENABLE_REAL_AI = if ($env:CAREER_ENABLE_REAL_AI) { $env:CAREER_ENABLE_REAL_AI } else { "false" }

if ($env:CAREER_ENABLE_REAL_AI -eq "true") {
  & (Join-Path $PSScriptRoot "bootstrap.ps1") -IncludeAi
} else {
  & (Join-Path $PSScriptRoot "bootstrap.ps1")
}

Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"

$startBackend = Assert-BackendPortAvailable -Port 8000
if ($startBackend) {
  if (-not (Test-Path -LiteralPath $Runtime)) {
    New-Item -ItemType Directory -Path $Runtime | Out-Null
  }
  $backendProcess = Start-Process -FilePath conda -ArgumentList @("run", "-n", "career-helper-app", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  Set-Content -LiteralPath $BackendPidFile -Value $backendProcess.Id
}

Push-Location $Frontend
try {
  conda run -n career-helper-app npm.cmd run dev
} finally {
  Pop-Location
}
