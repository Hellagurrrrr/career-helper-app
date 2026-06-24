$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

$env:CAREER_ENABLE_REAL_AI = "false"

& (Join-Path $PSScriptRoot "bootstrap.ps1") -Dev

conda run -n career-helper-app python -m pip check
conda run -n career-helper-app python -m pytest tests/test_smoke.py

Push-Location $Frontend
try {
  conda run -n career-helper-app npm.cmd run build
  conda run -n career-helper-app npm.cmd audit --audit-level=high
} finally {
  Pop-Location
}
