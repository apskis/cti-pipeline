#!/usr/bin/env bash
# One entrypoint, all components.
#   COMPONENT       selects components/<name>/task.md
#   MODEL_BACKEND   bedrock | subscription  (which model runtime)
#   CLOUD           aws | azure             (where output is shipped)
# Secrets arrive as ENV (Secrets Manager on AWS / Key Vault on Azure); the run
# scripts prefer env per-credential, so no vault is contacted. Do NOT set KEY_VAULT_URL.
set -euo pipefail
cd /app

: "${COMPONENT:?set COMPONENT (bulletin-scan|perimeter-scan|threat-hunting|reporting|program-console|documentation-sync)}"
: "${MODEL_BACKEND:=bedrock}"
: "${OUTPUT_DIR:=/app/out}"
# MODE only matters for the reporting component (weekly|quarterly); harmless elsewhere.
: "${MODE:=weekly}"
export MODE
mkdir -p "$OUTPUT_DIR"

# --- Model backend selection -------------------------------------------------
# bedrock:      Claude on Amazon Bedrock. AWS creds come from the task role (no key).
#               ANTHROPIC_MODEL must be a Bedrock inference-profile id.
# subscription: Claude Code on a Pro/Max plan via a long-lived OAuth token
#               (from `claude setup-token`). Set ANTHROPIC_MODEL=opus to pin Opus.
case "$MODEL_BACKEND" in
  bedrock)
    : "${ANTHROPIC_MODEL:?set ANTHROPIC_MODEL to a Bedrock inference-profile id}"
    : "${AWS_REGION:=us-east-1}"
    export CLAUDE_CODE_USE_BEDROCK=1
    echo "[entrypoint] model backend: Bedrock  model=$ANTHROPIC_MODEL region=$AWS_REGION"
    ;;
  subscription)
    : "${CLAUDE_CODE_OAUTH_TOKEN:?set CLAUDE_CODE_OAUTH_TOKEN (from 'claude setup-token') for subscription mode}"
    unset CLAUDE_CODE_USE_BEDROCK || true
    echo "[entrypoint] model backend: Claude subscription${ANTHROPIC_MODEL:+  model=$ANTHROPIC_MODEL}"
    ;;
  *) echo "unknown MODEL_BACKEND=$MODEL_BACKEND (use bedrock|subscription)"; exit 2 ;;
esac

CDIR="components/${COMPONENT}"
[ -d "$CDIR" ] || { echo "unknown COMPONENT=$COMPONENT"; exit 2; }
TASK="$CDIR/task.md"

# Skills are resolved from core/ (/app/.claude is a symlink to it; CLAUDE_PROJECT_DIR too).
export CLAUDE_PROJECT_DIR=/app/core

# Restore prior state from the object store first, so the dedup log, registers, IDs
# and earlier deliverables are on disk and the run reports only new or changed items.
# (Azure restore via blob download-batch is a follow up; AWS is the POC target.)
export OUTPUT_DIR REPO_ROOT=/app
if [ "${CLOUD:-aws}" = "aws" ]; then
  : "${OUTPUT_BUCKET:?set OUTPUT_BUCKET}"
  echo "[entrypoint] restoring prior state from s3://${OUTPUT_BUCKET}/${COMPONENT}/"
  aws s3 sync "s3://${OUTPUT_BUCKET}/${COMPONENT}/" "$OUTPUT_DIR" --only-show-errors
fi

# Output layout: every config/paths.json key resolves under OUTPUT_DIR and is created
# now, so a wrong path fails here rather than when a finished document is saved.
python3 scripts/resolve_paths.py
python3 scripts/update_state.py snapshot

# MCP servers: one stdio server per name in the component's enabled_servers. Keys are
# already in the environment, so the generated file carries no credential.
MCP_CONFIG=/app/.mcp.json
python3 deploy/gen_mcp_config.py --component "$COMPONENT" --repo /app --out "$MCP_CONFIG"

echo "[entrypoint] component=$COMPONENT mode=$MODE cloud=${CLOUD:-aws}"
# --settings loads the repo allow/deny list explicitly: headless runs have no trust
# dialog, and an untrusted workspace's .claude/settings.json permissions are ignored.
claude --print --permission-mode acceptEdits \
  --settings /app/core/.claude/settings.json \
  --mcp-config "$MCP_CONFIG" --strict-mcp-config \
  "Read ${TASK} and run it in full for today. The MODE environment variable is '${MODE}'. Write outputs under ${OUTPUT_DIR}. Report what you saved and where."

# Reporting is the analysis layer only: Claude wrote analysis_result.json, and the
# deterministic renderer turns it into the branded .docx here (no model call).
if [ "$COMPONENT" = "reporting" ]; then
  ANALYSIS="${OUTPUT_DIR}/analysis_result.json"
  [ -f "$ANALYSIS" ] || { echo "[entrypoint] reporting: ${ANALYSIS} missing — analysis did not complete"; exit 4; }
  echo "[entrypoint] rendering ${MODE} report from ${ANALYSIS}"
  python core/tools/reporting/render_report.py --mode "$MODE" \
    --analysis "$ANALYSIS" --out-dir "$OUTPUT_DIR"
fi

# Deterministic state: next IDs and a deliverables index from what is on disk, so the
# next run dedups correctly even if the model forgot to update its log.
python3 scripts/update_state.py finalize

# Ship output to the cloud's object store (a full copy: sync can skip a rewritten
# file whose size did not change, and losing a state update costs a whole run).
case "${CLOUD:-aws}" in
  aws)   : "${OUTPUT_BUCKET:?set OUTPUT_BUCKET}"
         aws s3 cp "$OUTPUT_DIR" "s3://${OUTPUT_BUCKET}/${COMPONENT}/" --recursive --only-show-errors ;;
  azure) : "${STORAGE_ACCOUNT:?}" ; : "${OUTPUT_CONTAINER:?}"
         az login --identity --allow-no-subscriptions >/dev/null
         az storage blob upload-batch -d "$OUTPUT_CONTAINER" -s "$OUTPUT_DIR" \
            --account-name "$STORAGE_ACCOUNT" --auth-mode login --overwrite true ;;
  *) echo "unknown CLOUD=${CLOUD}"; exit 2 ;;
esac
echo "[entrypoint] done; output shipped to ${CLOUD:-aws}"
