# Start the local, read only CTI console in one step (Windows PowerShell).
#   .\scripts\console.ps1                     # built page with the strict policy
#   .\scripts\console.ps1 -Build              # rebuild the page first, after a git pull
#   .\scripts\console.ps1 -Dev                # Vite dev server, reloads on edits
#   .\scripts\console.ps1 -Out D:\copy\out -Logs D:\copy\logs
# It starts the backend on 127.0.0.1:8765 and the page on 127.0.0.1:5173, opens the
# browser, and stops both when you press Ctrl+C. It reads out\ and logs\ and never
# writes to them, and it makes no model calls.
param(
  [switch]$Build,
  [switch]$Dev,
  [string]$Out,
  [string]$Logs,
  [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "console\backend"
$Frontend = Join-Path $Root "console\frontend"
$Api = "http://127.0.0.1:8765"
$Page = "http://127.0.0.1:5173"

function Test-Up([string]$Url) {
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $Url | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Wait-Up([string]$Url, [string]$What, [System.Diagnostics.Process]$Proc) {
  for ($i = 0; $i -lt 60; $i++) {
    if (Test-Up $Url) { return }
    if ($Proc -and $Proc.HasExited) { throw "$What stopped while starting; see the output above" }
    Start-Sleep -Milliseconds 500
  }
  throw "$What did not answer on $Url within 30 seconds"
}

# The backend reads these. Only set them when asked, so the defaults stay <repo>\out and
# <repo>\logs.
if ($Out) { $env:CTI_CONSOLE_OUT = (Resolve-Path $Out).Path }
if ($Logs) { $env:CTI_CONSOLE_LOGS = (Resolve-Path $Logs).Path }

# The repo standard is uv; a plain virtual environment works too.
$Venv = Join-Path $Backend ".venv\Scripts\python.exe"
if (Get-Command uv -ErrorAction SilentlyContinue) {
  $PyExe = "uv"
  $PyArgs = @("run", "python", "-m", "cti_console")
} elseif (Test-Path $Venv) {
  $PyExe = $Venv
  $PyArgs = @("-m", "cti_console")
} else {
  throw "no Python environment for the backend: see console\README.md, Backend"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found: install Node.js 20 or later"
}
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
  Write-Host "Installing the front end's packages, once."
  Push-Location $Frontend
  try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
  } finally {
    Pop-Location
  }
}
if (-not $Dev -and ($Build -or -not (Test-Path (Join-Path $Frontend "dist\index.html")))) {
  Write-Host "Building the page."
  Push-Location $Frontend
  try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
  } finally {
    Pop-Location
  }
}

$Started = @()
try {
  # A backend left running from an earlier start is reused, not replaced. It keeps
  # whatever -Out and -Logs it was started with.
  if (Test-Up "$Api/api/health") {
    Write-Host "Backend already running on $Api; using it."
  } else {
    Write-Host "Starting the backend on $Api."
    $Proc = Start-Process -FilePath $PyExe -ArgumentList $PyArgs -WorkingDirectory $Backend `
      -NoNewWindow -PassThru
    $Started += $Proc
    Wait-Up "$Api/api/health" "The backend" $Proc
  }

  if (Test-Up $Page) { throw "something already answers on $Page; stop it and try again" }
  $Script = if ($Dev) { "dev" } else { "preview" }
  Write-Host "Starting the page on $Page ($Script)."
  # npm is a .cmd shim, so it runs through cmd.exe to be started as a process.
  $Proc = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "npm", "run", $Script) `
    -WorkingDirectory $Frontend -NoNewWindow -PassThru
  $Started += $Proc
  Wait-Up $Page "The page" $Proc

  if (-not $NoBrowser) { Start-Process $Page }
  Write-Host "Console ready at $Page. Press Ctrl+C to stop it."
  Wait-Process -Id $Proc.Id
} finally {
  # Stop what this script started, children included (cmd.exe starts node).
  foreach ($P in $Started) {
    if (-not $P.HasExited) { & taskkill.exe /PID $P.Id /T /F | Out-Null }
  }
}
