param(
  [switch]$Dev,
  [switch]$IncludeAi
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$StateDir = Join-Path $Root ".cache\bootstrap"

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

function Get-CombinedHash {
  param([string[]]$Paths)

  $content = foreach ($Path in $Paths) {
    if (Test-Path $Path) {
      (Get-FileHash -Algorithm SHA256 $Path).Hash
    }
  }

  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes(($content -join "`n"))
  return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
}

function Sync-Stamp {
  param(
    [string]$Name,
    [string]$Hash,
    [scriptblock]$Install
  )

  $StampPath = Join-Path $StateDir "$Name.sha256"
  if ((Test-Path $StampPath) -and ((Get-Content $StampPath -Raw).Trim() -eq $Hash)) {
    return
  }

  & $Install
  Set-Content -Path $StampPath -Value $Hash
}

$RuntimeRequirements = Join-Path $Root "requirements.txt"
$DevRequirements = Join-Path $Root "requirements-dev.txt"
$AiRequirementsFile = Join-Path $Root "requirements-ai.txt"

$PythonRequirements = @($RuntimeRequirements)
$PythonInstallFile = $RuntimeRequirements
$PythonStamp = "python"

if ($Dev) {
  $PythonRequirements += $DevRequirements
  $PythonInstallFile = $DevRequirements
  $PythonStamp = "python-dev"
}

$PythonHash = Get-CombinedHash $PythonRequirements
Sync-Stamp $PythonStamp $PythonHash {
  conda run -n career-helper-app python -m pip install -r $PythonInstallFile
}

if ($IncludeAi) {
  $AiRequirements = $PythonRequirements + @($AiRequirementsFile)
  $AiHash = Get-CombinedHash $AiRequirements
  Sync-Stamp "python-ai" $AiHash {
    conda run -n career-helper-app python -m pip install -r $AiRequirementsFile
  }
}

$NodeInputs = @(
  (Join-Path $Frontend "package.json"),
  (Join-Path $Frontend "package-lock.json")
)
$NodeModules = Join-Path $Frontend "node_modules"
$NodeHash = Get-CombinedHash $NodeInputs

Sync-Stamp "frontend" $NodeHash {
  Push-Location $Frontend
  try {
    conda run -n career-helper-app npm.cmd ci
  } finally {
    Pop-Location
  }
}

if (-not (Test-Path $NodeModules)) {
  Push-Location $Frontend
  try {
    conda run -n career-helper-app npm.cmd ci
  } finally {
    Pop-Location
  }
}
