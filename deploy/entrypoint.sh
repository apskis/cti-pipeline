#!/usr/bin/env bash
# One entrypoint, all components. Select with COMPONENT; select cloud with CLOUD.
# Secrets arrive as ENV (Secrets Manager on AWS / Key Vault on Azure); the run
# scripts prefer env per-credential, so no vault is contacted. Do NOT set KEY_VAULT_URL.
set -euo pipefail
cd /app

: "${COMPONENT:?set COMPONENT (bulletin-scan|perimeter-scan|threat-hunting|program-console|documentation-sync)}"
: "${ANTHROPIC_MODEL:?set ANTHROPIC_MODEL to a Bedrock inference-profile id}"
: "${AWS_REGION:=us-east-1}"
: "${OUTPUT_DIR:=/app/out}"
export CLAUDE_CODE_USE_BEDROCK=1
mkdir -p "$OUTPUT_DIR"

CDIR="components/${COMPONENT}"
[ -d "$CDIR" ] || { echo "unknown COMPONENT=$COMPONENT"; exit 2; }
TASK="$CDIR/task.md"

# Skills and MCP config are resolved from core/ (CLAUDE_PROJECT_DIR points there).
export CLAUDE_PROJECT_DIR=/app/core

echo "[entrypoint] component=$COMPONENT cloud=${CLOUD:-aws} model=$ANTHROPIC_MODEL"
claude --print --permission-mode acceptEdits \
  "Read ${TASK} and run it in full for today. Write outputs under ${OUTPUT_DIR}. Report what you saved and where."

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
