param(
  [Alias("WithLlm")]
  [switch]$EnableLlm
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$Dist = Join-Path $Frontend "dist"

. (Join-Path $PSScriptRoot "lib\ports.ps1")

$UseLlm = [bool]$EnableLlm
$env:CAREER_ENABLE_REAL_AI = if ($UseLlm) { "true" } else { "false" }

if ($UseLlm) {
  & (Join-Path $PSScriptRoot "bootstrap.ps1") -IncludeAi
} else {
  & (Join-Path $PSScriptRoot "bootstrap.ps1")
}

if ($UseLlm) {
  Write-Host "Checking LLM connectivity before startup..."
  $CheckScriptPath = Join-Path $Root ".cache\llm-connectivity-check.py"
  $CheckScriptDir = Split-Path -Parent $CheckScriptPath
  New-Item -ItemType Directory -Force -Path $CheckScriptDir | Out-Null

  Set-Content -Path $CheckScriptPath -Encoding UTF8 -Value @'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.llm.models import Purpose, get_llm

llm = get_llm(Purpose.CV)
response = llm.invoke("Reply with exactly the word: pong")
text = getattr(response, "content", response)
if not isinstance(text, str) or not text.strip():
    raise RuntimeError("LLM returned an empty response.")
print(f"LLM connectivity OK: model={settings.llm_cv_model}, reply={text.strip()!r}")
'@

  Push-Location $Root
  try {
    conda run -n career-helper-app python $CheckScriptPath
    if ($LASTEXITCODE -ne 0) {
      throw "LLM connectivity check failed. Startup aborted."
    }
  } finally {
    Pop-Location
    Remove-Item -LiteralPath $CheckScriptPath -Force -ErrorAction SilentlyContinue
  }
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
