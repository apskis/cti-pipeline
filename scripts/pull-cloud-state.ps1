# One-time copy of the cloud deployment's state into out\ (Windows PowerShell).
# Read only on the AWS side; needs the AWS CLI and read access to the output bucket.
#   .\scripts\pull-cloud-state.ps1
#   .\scripts\pull-cloud-state.ps1 -Bucket my-other-bucket
param([string]$Bucket = "cti-pipeline-out-574625227402")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Get-ChildItem components -Directory | ForEach-Object {
  Write-Host "== $($_.Name)"
  aws s3 sync "s3://$Bucket/$($_.Name)/" "out\$($_.Name)\" --only-show-errors
  if ($LASTEXITCODE -ne 0) { throw "sync failed for $($_.Name)" }
}
Write-Host "state copied into out\"
