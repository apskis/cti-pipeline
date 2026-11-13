# One-time copy of the cloud deployment's state into out\ (Windows PowerShell).
# Read only on the AWS side; needs the AWS CLI and read access to the output bucket.
#   .\scripts\pull-cloud-state.ps1 -Bucket my-bucket
#   .\scripts\pull-cloud-state.ps1 -Bucket my-bucket -Company acme   # another company's state
#
# The AWS deployment this defaulted to was torn down on 2026-10-06, bucket included, so
# there is no default any more: pass the bucket of a live deployment, or seed from a zip
# export instead (docs/local-setup.md step 4).
param(
  [string]$Bucket,
  [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')][string]$Company = "genelabs"
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not $Bucket) {
  Write-Host "usage: .\scripts\pull-cloud-state.ps1 -Bucket <bucket>"
  Write-Host ""
  Write-Host "No default bucket: the cti-pipeline-out-574625227402 deployment was deleted."
  Write-Host "To seed from a zip export instead, see docs/local-setup.md step 4."
  exit 2
}
# The layouts the entrypoint writes: GeneLabs at the bucket root, others under a prefix.
if ($Company -eq "genelabs") { $Src = ""; $Dest = "out" }
else { $Src = "companies/$Company/"; $Dest = "data\companies\$Company\out" }
Get-ChildItem components -Directory | ForEach-Object {
  Write-Host "== $($_.Name)"
  aws s3 sync "s3://$Bucket/$Src$($_.Name)/" "$Dest\$($_.Name)\" --only-show-errors
  if ($LASTEXITCODE -ne 0) { throw "sync failed for $($_.Name)" }
}
Write-Host "state copied into $Dest\"
