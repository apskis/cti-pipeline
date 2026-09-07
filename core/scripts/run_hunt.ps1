# CTI Threat Hunting Automation runner — Claude Code on Bedrock; MCP creds resolved by cti-feeds launchers from Key Vault (Windows)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $PSScriptRoot; Set-Location $Here

if (-not (Test-Path ".env")) { throw ".env not found. Copy .env.example to .env and fill it in." }
Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
  $k,$v = $_ -split '=',2
  [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
}
foreach ($v in @("CTI_ROOT","CTI_FEEDS_DIR","KEY_VAULT_URL","AWS_REGION","ANTHROPIC_MODEL")) {
  if (-not [Environment]::GetEnvironmentVariable($v,"Process")) { throw "Set $v in .env" }
}
$env:CLAUDE_CODE_USE_BEDROCK = "1"
Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

if (-not $env:AZURE_CLIENT_ID) {
  try { az account show *> $null } catch { Write-Host "NOTE: run 'az login' so the launchers can read Key Vault (no AZURE_* SP set)." }
}

$prompt = (Get-Content task/LOCAL_OVERRIDES.md -Raw) + "`n---`n" + (Get-Content task/cti-threat-hunting-task.md -Raw)
claude -p $prompt `
  --mcp-config .mcp.json `
  --add-dir "$env:CTI_ROOT" `
  --model "$env:ANTHROPIC_MODEL" `
  --permission-mode acceptEdits
