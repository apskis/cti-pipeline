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

docker image inspect $Image *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
  docker build -f deploy/Dockerfile -t $Image .
  if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
}

$Out = Join-Path (Get-Location) "out\$Component"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
docker run --rm --env-file .env `
  -e COMPONENT=$Component -e MODE=$Mode -e CLOUD=local `
  -v "${Out}:/app/out" $Image
Write-Host "output: out\$Component\"
