#!/usr/bin/env bash
# Run one component on this machine, with no cloud and no container.
#
#   ./scripts/run_local.sh                      # bulletin-scan
#   ./scripts/run_local.sh perimeter-scan
#   MODE=quarterly ./scripts/run_local.sh reporting
#   OUTPUT_DIR=~/OneDrive/CTI ./scripts/run_local.sh
#
# The model runs on the Claude subscription already signed in to the CLI, so a run
# costs nothing per token. Set CLAUDE_CODE_OAUTH_TOKEN only for an unattended machine
# where no interactive login exists.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPONENT="${1:-bulletin-scan}"
[ -d "$REPO_ROOT/components/$COMPONENT" ] || {
  echo "unknown component '$COMPONENT'. Available:"
  (cd "$REPO_ROOT/components" && ls -1d */ | tr -d /) | sed 's/^/  /'
  exit 2
}

# One shared output folder for every component, unlike the cloud layout which gave each
# its own prefix and so its own diverging dedup log and register. Sharing is what the
# dedup and next-ID logic actually wants, and only bulletin-scan writes documents.
export OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/out}"
export COMPONENT MODEL_BACKEND=subscription CLOUD=local
export MODE="${MODE:-weekly}"

command -v claude >/dev/null || { echo "claude CLI not found: install Claude Code first"; exit 2; }
python3 - <<'PY' || exit 2
import sys
missing = [m for m in ("docx", "openpyxl", "yaml") if not __import__("importlib.util", fromlist=["x"]).find_spec(m)]
if missing:
    print("missing Python packages: " + ", ".join(missing))
    print("install them with:  pip install -r deploy/requirements.txt")
    sys.exit(2)
PY

# Which API keys this component's MCP servers need, so a missing one is named up front
# rather than surfacing as an empty result mid run.
case "$COMPONENT" in
  bulletin-scan|reporting) NEEDED="NVD_API_KEY OTX_API_KEY" ;;
  perimeter-scan)          NEEDED="SHODAN_API_KEY NVD_API_KEY OTX_API_KEY" ;;
  threat-hunting)          NEEDED="SPLUNK_URL SPLUNK_TOKEN" ;;
  *)                       NEEDED="" ;;
esac
for var in $NEEDED; do
  [ -n "${!var:-}" ] || echo "[run_local] warning: $var is not set; its MCP server will return nothing"
done

echo "[run_local] component=$COMPONENT output=$OUTPUT_DIR"
exec "$REPO_ROOT/deploy/entrypoint.sh"
