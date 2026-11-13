# Share the console through a Microsoft dev tunnel, with sign in on (Windows PowerShell).
#   .\scripts\console-share.ps1           # start the console and host the tunnel
#   .\scripts\console-share.ps1 -Build    # rebuild the page first, after a git pull
# One time setup, and what each setting means: docs\console-share.md. Settings come from
# .env.console at the repo root, which git ignores. The console is reachable only while
# this runs; Ctrl+C stops the tunnel and the console together.
param([switch]$Build)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "console\backend"
$Frontend = Join-Path $Root "console\frontend"
$Dist = Join-Path $Frontend "dist"
$Api = "http://127.0.0.1:8765"
$EnvFile = Join-Path $Root ".env.console"
$Needed = @(
  "CTI_TUNNEL_ID", "CTI_CONSOLE_URL", "CTI_OIDC_ISSUER", "CTI_OIDC_CLIENT_ID",
  "CTI_OIDC_CLIENT_SECRET", "CTI_SESSION_SECRET"
)

function Test-Up([string]$Url) {
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $Url | Out-Null
    return $true
  } catch {
    return $false
  }
}

if (-not (Test-Path $EnvFile)) {
  throw "missing .env.console: copy .env.console.example to .env.console and fill it in (docs\console-share.md)"
}
# KEY=VALUE lines, read into this process only, so no secret is printed or written anywhere.
$Settings = @{}
foreach ($Line in Get-Content $EnvFile) {
  $Text = $Line.Trim()
  if (-not $Text -or $Text.StartsWith("#")) { continue }
  $Pair = $Text -split "=", 2
  if ($Pair.Count -ne 2) { throw "a line in .env.console has no '=': $($Pair[0])" }
  $Settings[$Pair[0].Trim()] = $Pair[1].Trim().Trim('"')
}
foreach ($Name in $Needed) {
  if (-not $Settings[$Name]) { throw "set $Name in .env.console" }
}
if (-not $Settings["CTI_CONSOLE_URL"].StartsWith("https://")) {
  throw "CTI_CONSOLE_URL must be the tunnel's https address (devtunnel show $($Settings["CTI_TUNNEL_ID"]))"
}
if (-not (Get-Command devtunnel -ErrorAction SilentlyContinue)) {
  throw "devtunnel not found: install it with 'winget install Microsoft.devtunnel', then see docs\console-share.md"
}
# A console already on the port may be the local one with sign in off. The tunnel must
# reach one that started with sign in on, so this script starts its own.
if (Test-Up "$Api/api/health") {
  throw "something already answers on ${Api}: stop the local console first (Ctrl+C in its window)"
}

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

if ($Build -or -not (Test-Path (Join-Path $Dist "index.html"))) {
  Write-Host "Building the page."
  Push-Location $Frontend
  try {
    if (-not (Test-Path "node_modules")) {
      npm ci
      if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
  } finally {
    Pop-Location
  }
}

# The backend inherits these. They are set for this process only, never saved.
foreach ($Key in $Settings.Keys) {
  [Environment]::SetEnvironmentVariable($Key, $Settings[$Key], "Process")
}
$env:CTI_AUTH = "oidc"
$env:CTI_CONSOLE_STATIC = $Dist

$Tunnel = $Settings["CTI_TUNNEL_ID"]
$Server = $null
$LaunchedAt = Get-Date
try {
  Write-Host "Starting the console with sign in on."
  $Server = Start-Process -FilePath $PyExe -ArgumentList $PyArgs -WorkingDirectory $Backend `
    -NoNewWindow -PassThru
  for ($i = 0; -not (Test-Up "$Api/api/health"); $i++) {
    if ($Server.HasExited) { throw "the console stopped while starting; see the output above" }
    if ($i -ge 60) { throw "the console did not answer within 30 seconds" }
    Start-Sleep -Milliseconds 500
  }

  # A persistent tunnel lasts at most 30 days; each start renews it, so it never lapses
  # while in use.
  devtunnel update $Tunnel --expiration 30d | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "devtunnel could not renew tunnel $Tunnel; run 'devtunnel user login' and try again" }

  Write-Host "Sharing at $($Settings["CTI_CONSOLE_URL"]). Press Ctrl+C to stop."
  devtunnel host $Tunnel
} finally {
  if ($Server -and -not $Server.HasExited) { & taskkill.exe /PID $Server.Id /T /F | Out-Null }
  # The backend keeps a hidden Word open to make branded PDFs; close only Word started
  # for automation since this launch, never a Word window you have open.
  Get-CimInstance Win32_Process -Filter "Name='WINWORD.EXE'" |
    Where-Object { $_.CommandLine -match '/Automation' -and $_.CreationDate -ge $LaunchedAt } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
