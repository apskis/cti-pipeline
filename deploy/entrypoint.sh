#!/usr/bin/env bash
# One entrypoint, all components.
#   COMPONENT       selects components/<name>/task.md
#   MODEL_BACKEND   bedrock | subscription     (which model runtime)
#   CLOUD           aws | azure | local        (where output is shipped)
# Secrets arrive as ENV (Secrets Manager on AWS / Key Vault on Azure); the run
# scripts prefer env per-credential, so no vault is contacted. Do NOT set KEY_VAULT_URL.
set -euo pipefail

# Resolve the repo from this script's location rather than assuming /app, so the same
# entrypoint serves the container (/app/deploy/entrypoint.sh -> /app) and a developer
# machine (scripts/run_local.sh). REPO_ROOT may be set explicitly to override.
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_ROOT"

: "${COMPONENT:?set COMPONENT (bulletin-scan|perimeter-scan|threat-hunting|reporting|program-console|documentation-sync)}"
: "${MODEL_BACKEND:=bedrock}"
: "${OUTPUT_DIR:=$REPO_ROOT/out}"
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
    # In a container the token is the only credential available. On a developer machine
    # an interactive `claude login` has already stored one, so the token is optional
    # there and the CLI's own credential is used.
    unset CLAUDE_CODE_USE_BEDROCK || true
    if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
      echo "[entrypoint] model backend: Claude subscription, OAuth token${ANTHROPIC_MODEL:+  model=$ANTHROPIC_MODEL}"
    elif claude --version >/dev/null 2>&1; then
      echo "[entrypoint] model backend: Claude subscription, signed-in CLI${ANTHROPIC_MODEL:+  model=$ANTHROPIC_MODEL}"
    else
      echo "no Claude credential: run 'claude login', or set CLAUDE_CODE_OAUTH_TOKEN from 'claude setup-token'"
      exit 2
    fi
    ;;
  *) echo "unknown MODEL_BACKEND=$MODEL_BACKEND (use bedrock|subscription)"; exit 2 ;;
esac

CDIR="components/${COMPONENT}"
[ -d "$CDIR" ] || { echo "unknown COMPONENT=$COMPONENT"; exit 2; }
TASK="$CDIR/task.md"

# Skills are resolved from core/ (in the image REPO_ROOT/.claude is a symlink to it, and
# CLAUDE_PROJECT_DIR points there; locally this variable alone is enough).
export CLAUDE_PROJECT_DIR="$REPO_ROOT/core"

# Restore prior state from the object store first, so the dedup log, registers, IDs
# and earlier deliverables are on disk and the run reports only new or changed items.
# local needs no restore: the state never left the disk it is about to be read from.
# (Azure restore via blob download-batch is a follow up; AWS was the POC target.)
export OUTPUT_DIR REPO_ROOT
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
MCP_CONFIG="$REPO_ROOT/.mcp.json"
python3 deploy/gen_mcp_config.py --component "$COMPONENT" --repo "$REPO_ROOT" --out "$MCP_CONFIG"

echo "[entrypoint] component=$COMPONENT mode=$MODE cloud=${CLOUD:-aws}"
# --settings loads the repo allow/deny list explicitly: headless runs have no trust
# dialog, and an untrusted workspace's .claude/settings.json permissions are ignored.
claude --print --permission-mode acceptEdits \
  --settings "$REPO_ROOT/core/.claude/settings.json" \
  --mcp-config "$MCP_CONFIG" --strict-mcp-config \
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
  for pass in $(seq 1 "${BUILD_PASSES:-8}"); do
    python3 scripts/pending_deliverables.py --batch "${BUILD_BATCH:-4}" --out "$PENDING" && rc=0 || rc=$?
    [ "$rc" -eq 0 ] || break     # 3 = nothing pending
    echo "[entrypoint] builder pass $pass"
    claude --print --permission-mode acceptEdits \
      --settings "$REPO_ROOT/core/.claude/settings.json" \
      --mcp-config "$MCP_CONFIG" --strict-mcp-config \
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
         aws s3 cp "$OUTPUT_DIR" "s3://${OUTPUT_BUCKET}/${COMPONENT}/" --recursive --only-show-errors
         echo "[entrypoint] done; output shipped to aws" ;;
  azure) : "${STORAGE_ACCOUNT:?}" ; : "${OUTPUT_CONTAINER:?}"
         az login --identity --allow-no-subscriptions >/dev/null
         az storage blob upload-batch -d "$OUTPUT_CONTAINER" -s "$OUTPUT_DIR" \
            --account-name "$STORAGE_ACCOUNT" --auth-mode login --overwrite true
         echo "[entrypoint] done; output shipped to azure" ;;
  local) echo "[entrypoint] done; output is in $OUTPUT_DIR" ;;
  *) echo "unknown CLOUD=${CLOUD} (use aws|azure|local)"; exit 2 ;;
esac
