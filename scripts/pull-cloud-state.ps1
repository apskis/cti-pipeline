# One-time copy of the cloud deployment's state into out\ (Windows PowerShell).
# Read only on the AWS side; needs the AWS CLI and read access to the output bucket.
#   .\scripts\pull-cloud-state.ps1 -Bucket my-bucket
#
# The AWS deployment this defaulted to was torn down on 2026-10-06, bucket included, so
# there is no default any more: pass the bucket of a live deployment, or seed from a zip
# export instead (docs/local-setup.md step 4).
param([string]$Bucket)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not $Bucket) {
  Write-Host "usage: .\scripts\pull-cloud-state.ps1 -Bucket <bucket>"
  Write-Host ""
  Write-Host "No default bucket: the cti-pipeline-out-574625227402 deployment was deleted."
  Write-Host "To seed from a zip export instead, see docs/local-setup.md step 4."
  exit 2
}
Get-ChildItem components -Directory | ForEach-Object {
  Write-Host "== $($_.Name)"
  aws s3 sync "s3://$Bucket/$($_.Name)/" "out\$($_.Name)\" --only-show-errors
  if ($LASTEXITCODE -ne 0) { throw "sync failed for $($_.Name)" }
}
Write-Host "state copied into out\"
