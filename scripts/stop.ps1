$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "lib\ports.ps1")

$Runtime = Join-Path $Root ".cache\runtime"
$BackendPidFile = Join-Path $Runtime "backend.pid"
$ports = @(8000, 5173)

function Invoke-DevShutdown {
  param(
    [int]$Port = 8000
  )

  if (-not (Test-BackendHealth -Port $Port)) {
    return $false
  }

  Write-Host "Requesting backend shutdown on port $Port..."
  try {
    Invoke-RestMethod `
      -Uri "http://127.0.0.1:$Port/__dev/shutdown" `
      -Method Post `
      -Headers @{ "X-Dev-Action" = "shutdown" } `
      -TimeoutSec 2 | Out-Null
  } catch {
    return $false
  }

  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 250
    if (-not (Test-BackendHealth -Port $Port)) {
      Write-Host "Backend shutdown confirmed."
      return $true
    }
  }

  return $false
}

function Stop-PidFileProcess {
  param(
    [string]$PidFile
  )

  if (-not (Test-Path -LiteralPath $PidFile)) {
    return
  }

  $rawPid = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  $processId = 0
  if (-not [int]::TryParse($rawPid, [ref]$processId)) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    return
  }

  if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    return
  }

  Write-Host "Stopping recorded backend launcher PID $processId..."
  Stop-PortOwner -ProcessId $processId | Out-Null
  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-CareerHelperPythonBackends {
  $processes = Get-Process python -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Path -and
      ($_.Path -like "*\career-helper-app\python.exe" -or $_.Path -like "*\career-helper-app\pythonw.exe")
    }

  foreach ($process in $processes) {
    Write-Host "Stopping career-helper Python backend candidate PID $($process.Id) ($($process.Path))..."
    Stop-PortOwner -ProcessId $process.Id | Out-Null
  }
}

function Stop-PortOwner {
  param(
    [Parameter(Mandatory = $true)]
    [int]$ProcessId
  )

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($process) {
    try {
      Stop-Process -Id $ProcessId -Force -ErrorAction Stop
      return $true
    } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
      Write-Host "Stop-Process could not stop PID $ProcessId. Trying taskkill..."
    }
  } else {
    Write-Host "PID $ProcessId is not visible to Get-Process. Trying taskkill..."
  }

  $taskkill = Join-Path $env:SystemRoot "System32\taskkill.exe"
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $taskkill /PID $ProcessId /T /F 2>&1
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($LASTEXITCODE -eq 0) {
    return $true
  }

  $message = (
    $output | ForEach-Object {
      if ($_ -is [System.Management.Automation.ErrorRecord]) {
        $_.Exception.Message
      } else {
        $_.ToString()
      }
    } | Out-String
  ).Trim()
  if ($message) {
    Write-Warning $message
  }
  Write-Warning "Could not stop PID $ProcessId. If access is denied, run this script from an elevated PowerShell window."
  return $false
}

Invoke-DevShutdown -Port 8000 | Out-Null
Stop-PidFileProcess -PidFile $BackendPidFile
if (Test-BackendHealth -Port 8000) {
  Stop-CareerHelperPythonBackends
  Start-Sleep -Milliseconds 500
}

foreach ($port in $ports) {
  $owner = Get-ListeningProcess -Port $port
  if (-not $owner) {
    Write-Host "Port $port is not in use."
    continue
  }

  Write-Host "Stopping PID $($owner.Id) ($($owner.ProcessName)) on port $port..."
  $stopped = Stop-PortOwner -ProcessId $owner.Id
  Start-Sleep -Milliseconds 300

  $remaining = Get-ListeningProcess -Port $port
  if (-not $remaining) {
    Write-Host "Port $port is now free."
  } elseif ($stopped) {
    Write-Warning "Stop command completed, but port $port is still in use by PID $($remaining.Id) ($($remaining.ProcessName))."
  }
}
