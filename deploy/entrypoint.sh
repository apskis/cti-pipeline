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

# Skills and MCP config are resolved from core/ (CLAUDE_PROJECT_DIR points there).
export CLAUDE_PROJECT_DIR=/app/core

echo "[entrypoint] component=$COMPONENT mode=$MODE cloud=${CLOUD:-aws}"
claude --print --permission-mode acceptEdits \
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

# Ship output to the cloud's object store
case "${CLOUD:-aws}" in
  aws)   : "${OUTPUT_BUCKET:?set OUTPUT_BUCKET}"
         aws s3 cp "$OUTPUT_DIR" "s3://${OUTPUT_BUCKET}/${COMPONENT}/" --recursive ;;
  azure) : "${STORAGE_ACCOUNT:?}" ; : "${OUTPUT_CONTAINER:?}"
         az storage blob upload-batch -d "$OUTPUT_CONTAINER" -s "$OUTPUT_DIR" \
            --account-name "$STORAGE_ACCOUNT" --auth-mode login --overwrite true ;;
  *) echo "unknown CLOUD=${CLOUD}"; exit 2 ;;
esac
echo "[entrypoint] done; output shipped to ${CLOUD:-aws}"
