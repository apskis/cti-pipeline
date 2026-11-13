# Run one pipeline component on this machine (Windows PowerShell), on your Claude plan.
#   .\scripts\run-local.ps1 bulletin-scan
#   .\scripts\run-local.ps1 reporting -Build          # rebuild after a git pull
#   .\scripts\run-local.ps1 reporting -Mode quarterly
#   .\scripts\run-local.ps1 bulletin-scan -Company acme   # run for another company
# State lives in out\<component>\, the same layout as the S3 bucket. Any company but
# GeneLabs keeps it in data\companies\<slug>\out\<component>\, where the console reads it.
param(
  [Parameter(Mandatory = $true)][string]$Component,
  [switch]$Build,
  [string]$Mode = "weekly",
  [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')][string]$Company = "genelabs"
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

$CompanyDir = Join-Path (Get-Location) "data\companies\$Company"
if ($Company -eq "genelabs") { $Out = Join-Path (Get-Location) "out\$Component" }
else { $Out = Join-Path $CompanyDir "out\$Component" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
# One-off overrides from the shell win over .env, e.g. $env:SKIP_SCAN=1 to build only.
$Extra = @()
foreach ($Name in "SKIP_SCAN", "BUILD_PASSES", "REVIEW", "REVIEW_ALL", "REVIEW_MODEL") {
  $Value = [Environment]::GetEnvironmentVariable($Name)
  if ($Value) { $Extra += @("-e", "$Name=$Value") }
}
# The company folder the console keeps (brand, profile, notes), read only, so a save in
# the console reaches the next run. Without it the image uses the committed
# config\companies copy, which only GeneLabs and companies committed there have.
$Brand = @()
if (Test-Path (Join-Path $CompanyDir "company.json")) {
  $Brand = @("-v", "${CompanyDir}:/app/company:ro", "-e", "CTI_COMPANY_DIR=/app/company")
} elseif (-not (Test-Path "config\companies\$Company\company.json")) {
  throw "unknown company: $Company (add it in the console, Settings, Companies)"
}
docker run --rm --env-file $EnvFile `
  -e COMPONENT=$Component -e COMPANY=$Company -e MODE=$Mode -e CLOUD=local @Extra @Brand `
  -v "${Out}:/app/out" $Image
$Code = $LASTEXITCODE
Remove-Item $EnvFile -ErrorAction SilentlyContinue
Write-Host "output: $Out (exit $Code)"
