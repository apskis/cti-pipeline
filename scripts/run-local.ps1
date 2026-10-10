# Run one pipeline component on this machine (Windows PowerShell), on your Claude plan.
#   .\scripts\run-local.ps1 bulletin-scan
#   .\scripts\run-local.ps1 reporting -Build          # rebuild after a git pull
#   .\scripts\run-local.ps1 reporting -Mode quarterly
# State lives in out\<component>\, the same layout as the S3 bucket.
param(
  [Parameter(Mandatory = $true)][string]$Component,
  [switch]$Build,
  [string]$Mode = "weekly"
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Image = "cti-pipeline:local"

if (-not (Test-Path .env)) { throw "missing .env: copy .env.example to .env and fill it in" }
if (-not (Test-Path "components\$Component")) { throw "unknown component: $Component" }

# `docker image inspect` reports a missing image on stderr, and Windows PowerShell 5.1
# turns redirected native stderr into a terminating error under "Stop", so the first run
# died here instead of building. Listing prints nothing for a missing image.
$HaveImage = [bool](docker image ls -q $Image)
if ($Build -or -not $HaveImage) {
  docker build -f deploy/Dockerfile -t $Image .
  if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
}

# Notepad saves .env with CRLF, and docker --env-file keeps the trailing CR in each
# value, which silently corrupts the token. Pass docker an LF copy instead.
$EnvFile = Join-Path $env:TEMP "cti-pipeline.env"
[IO.File]::WriteAllText($EnvFile, ((Get-Content .env -Raw) -replace "`r", ""))

$Out = Join-Path (Get-Location) "out\$Component"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
docker run --rm --env-file $EnvFile `
  -e COMPONENT=$Component -e MODE=$Mode -e CLOUD=local `
  -v "${Out}:/app/out" $Image
$Code = $LASTEXITCODE
Remove-Item $EnvFile -ErrorAction SilentlyContinue
Write-Host "output: out\$Component\ (exit $Code)"
