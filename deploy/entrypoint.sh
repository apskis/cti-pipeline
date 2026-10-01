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

# program-console is a plain Python dashboard refresh. Starting a Claude session for it
# cost a full model run every hour and did nothing the script cannot, so it runs the
# script directly. The collector is not shipped in this sanitized build yet, so until it
# is, the job exits cleanly instead of paying for a session that can only fail.
if [ "$COMPONENT" = "program-console" ]; then
  if [ -x bin/refresh-console.sh ]; then
    exec bash bin/refresh-console.sh
  fi
  echo "[entrypoint] program-console: bin/refresh-console.sh not shipped in this image; nothing to do (no model call)"
  exit 0
fi

# --- Model backend selection -------------------------------------------------
# bedrock:      Claude on Amazon Bedrock. AWS creds come from the task role (no key).
#               ANTHROPIC_MODEL must be a Bedrock inference-profile id.
# subscription: Claude Code on a Pro/Max plan via a long-lived OAuth token
#               (from `claude setup-token`). Set ANTHROPIC_MODEL=opus to pin Opus.
# BUILD_MODEL:  model for the builder passes, which fill templates from a finished scan
#               and do not need the scan model. Defaults to Haiku 4.5 on either backend;
#               set BUILD_MODEL="$ANTHROPIC_MODEL" to build with the scan model again.
case "$MODEL_BACKEND" in
  bedrock)
    : "${ANTHROPIC_MODEL:?set ANTHROPIC_MODEL to a Bedrock inference-profile id}"
    : "${AWS_REGION:=us-east-1}"
    export CLAUDE_CODE_USE_BEDROCK=1
    : "${BUILD_MODEL:=us.anthropic.claude-haiku-4-5-20251001-v1:0}"
    echo "[entrypoint] model backend: Bedrock  model=$ANTHROPIC_MODEL region=$AWS_REGION"
    ;;
  subscription)
    : "${CLAUDE_CODE_OAUTH_TOKEN:?set CLAUDE_CODE_OAUTH_TOKEN (from 'claude setup-token') for subscription mode}"
    unset CLAUDE_CODE_USE_BEDROCK || true
    : "${BUILD_MODEL:=haiku}"
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

# run_claude LABEL [claude args...]: one headless session. JSON output carries the run's
# cost and turn count, so every session logs one [cost] line to CloudWatch and appends
# to state/cost-log.jsonl, which ships to the object store with the rest of the state.
# On the subscription backend the dollar figure is what the run would cost at API
# prices, not a bill. A failing session still fails the job, as before.
COST_LOG="$OUTPUT_DIR/state/cost-log.jsonl"
run_claude() {
  local label="$1"; shift
  local out rc=0
  out="$(mktemp)"
  claude --print --output-format json --permission-mode acceptEdits \
    --settings /app/core/.claude/settings.json \
    --mcp-config "$MCP_CONFIG" --strict-mcp-config "$@" > "$out" || rc=$?
  COMPONENT="$COMPONENT" MODE="$MODE" LABEL="$label" RC="$rc" \
    python3 deploy/log_cost.py "$out" "$COST_LOG" || true
  rm -f "$out"
  return "$rc"
}

echo "[entrypoint] component=$COMPONENT mode=$MODE cloud=${CLOUD:-aws}"
# --settings loads the repo allow/deny list explicitly: headless runs have no trust
# dialog, and an untrusted workspace's .claude/settings.json permissions are ignored.
run_claude scan \
  "Read ${TASK} and run it in full for today. The MODE environment variable is '${MODE}'. Write outputs under ${OUTPUT_DIR}. Report what you saved and where."

# Builder passes: a single headless session will not carry a dozen documents, so the
# scan pass only assigns IDs in the dedup log and each builder pass (fresh context)
# turns a small batch of them into files, until nothing is pending or the cap is hit.
BUILD_TASK="$CDIR/task-build.md"
if [ -f "$BUILD_TASK" ]; then
  PENDING="$OUTPUT_DIR/state/_work/pending.json"
  # A .failed.md marker takes an item out of the batch for the rest of the run so it stops
  # consuming a slot in every pass. Clearing them here keeps that block to one run: today's
  # run always retries what yesterday's could not build.
  rm -f "$OUTPUT_DIR"/state/_work/*.failed.md 2>/dev/null || true
  # Two passes of four by default: whatever is left stays pending in the dedup log and
  # the next run builds it, so a low cap delays documents rather than losing them.
  for pass in $(seq 1 "${BUILD_PASSES:-2}"); do
    python3 scripts/pending_deliverables.py --batch "${BUILD_BATCH:-4}" --out "$PENDING" && rc=0 || rc=$?
    [ "$rc" -eq 0 ] || break     # 3 = nothing pending
    echo "[entrypoint] builder pass $pass model=$BUILD_MODEL"
    run_claude "build-$pass" --model "$BUILD_MODEL" \
      "Read ${BUILD_TASK} and build every item listed in ${PENDING}. The output folder is ${OUTPUT_DIR}. Report one line per item."
  done
fi

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
