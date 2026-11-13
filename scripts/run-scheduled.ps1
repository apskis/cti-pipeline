# Task Scheduler entry point: make sure Docker is up, run one component, log to a file.
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run-scheduled.ps1 bulletin-scan
#   ...\run-scheduled.ps1 reporting -Mode weekly -Company acme
# Always local: run-local.ps1 sets CLOUD=local and mounts only the component's state.
param(
  [Parameter(Mandatory = $true)][string]$Component,
  [string]$Mode = "weekly",
  [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')][string]$Company = "genelabs"
)
$ErrorActionPreference = "Stop"
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Repo
# The console reads GeneLabs' logs from logs\ and every other company's from its folder.
if ($Company -eq "genelabs") { $Logs = Join-Path $Repo "logs" }
else { $Logs = Join-Path $Repo "data\companies\$Company\logs" }
New-Item -ItemType Directory -Force $Logs | Out-Null
$Log = Join-Path $Logs ("{0}-{1}-{2}.log" -f $Component, $Mode, (Get-Date -Format "yyyy-MM-dd-HHmm"))

function Test-Docker {
  # Asked through cmd so a stopped daemon's stderr is not a PowerShell error.
  cmd.exe /c "docker info >nul 2>&1"
  return $LASTEXITCODE -eq 0
}

if (-not (Test-Docker)) {
  $Desktop = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
    "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $Desktop) { "Docker Desktop not found" | Out-File -Encoding utf8 $Log; exit 1 }
  Start-Process $Desktop
  $Deadline = (Get-Date).AddMinutes(5)
  while (-not (Test-Docker)) {
    if ((Get-Date) -gt $Deadline) { "Docker did not start within 5 minutes" | Out-File -Encoding utf8 $Log; exit 1 }
    Start-Sleep -Seconds 5
  }
}

# The redirect is done by cmd, not PowerShell: Windows PowerShell 5.1 turns a redirected
# native command's stderr into a terminating error, which killed the first attempt.
$Runner = Join-Path $Repo "scripts\run-local.ps1"
cmd.exe /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" $Component -Mode $Mode -Company $Company > `"$Log`" 2>&1"
exit $LASTEXITCODE
