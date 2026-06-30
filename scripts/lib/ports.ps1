function Get-ListeningProcess {
  param(
    [Parameter(Mandatory = $true)]
    [int]$Port
  )

  $line = netstat -ano -p tcp | Select-String -Pattern "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)" | Select-Object -First 1
  if (-not $line) {
    return $null
  }

  $processId = [int]$line.Matches[0].Groups[1].Value
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue

  return [PSCustomObject]@{
    Id = $processId
    ProcessName = if ($process) { $process.ProcessName } else { "unknown" }
    Path = if ($process) { $process.Path } else { $null }
    Exists = [bool]$process
  }
}

function Test-BackendHealth {
  param(
    [int]$Port = 8000
  )

  try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
    return $response.status -eq "ok"
  } catch {
    return $false
  }
}

function Assert-BackendPortAvailable {
  param(
    [int]$Port = 8000
  )

  $owner = Get-ListeningProcess -Port $Port
  if (-not $owner) {
    return $true
  }

  if (Test-BackendHealth -Port $Port) {
    Write-Host "AI Career Helper is already running at http://127.0.0.1:$Port/ (PID $($owner.Id), $($owner.ProcessName))."
    return $false
  }

  $message = "Port $Port is already in use by PID $($owner.Id) ($($owner.ProcessName))."
  if ($owner.Path) {
    $message = "$message Path: $($owner.Path)"
  }
  throw "$message Stop that process or choose another port before starting AI Career Helper."
}
