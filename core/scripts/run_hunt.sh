#!/usr/bin/env bash
# CTI Threat Hunting Automation runner — Claude Code on Bedrock; MCP creds resolved by the cti-feeds
# launchers from Azure Key Vault (KEY_VAULT_URL), with .env overrides.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$HERE"

if [ -f .env ]; then set -a; . ./.env; set +a; else
  echo "ERROR: .env not found. Copy .env.example to .env and fill it in." >&2; exit 1; fi
: "${CTI_ROOT:?Set CTI_ROOT in .env}"
: "${CTI_FEEDS_DIR:?Set CTI_FEEDS_DIR in .env (path to your cti-feeds MCP launchers)}"
: "${KEY_VAULT_URL:?Set KEY_VAULT_URL in .env (or uncomment direct credentials)}"
: "${AWS_REGION:?Set AWS_REGION in .env}"
: "${ANTHROPIC_MODEL:?Set ANTHROPIC_MODEL (a Bedrock inference-profile id) in .env}"

export CLAUDE_CODE_USE_BEDROCK=1
unset ANTHROPIC_API_KEY || true

# The launchers use DefaultAzureCredential. If you are not using a service principal
# (AZURE_* in .env) or a managed identity, make sure you have run `az login`.
if [ -z "${AZURE_CLIENT_ID:-}" ] && command -v az >/dev/null 2>&1; then
  az account show >/dev/null 2>&1 || echo "NOTE: no AZURE_* service principal set and 'az login' session not found — run 'az login' so the launchers can read Key Vault." >&2
fi

PROMPT_FILE="$(mktemp)"
{ cat task/LOCAL_OVERRIDES.md; echo; echo '---'; echo; cat task/cti-threat-hunting-task.md; } > "$PROMPT_FILE"
# Every uncommented .env override is now exported and inherited by the launcher subprocesses.
claude -p "$(cat "$PROMPT_FILE")" \
  --mcp-config .mcp.json \
  --add-dir "$CTI_ROOT" \
  --model "$ANTHROPIC_MODEL" \
  --permission-mode acceptEdits
rm -f "$PROMPT_FILE"
