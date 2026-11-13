#!/usr/bin/env bash
# Run one pipeline component on this machine, on your Claude plan, with no cloud account.
#   scripts/run-local.sh bulletin-scan            # build image if missing, then run
#   scripts/run-local.sh reporting --build        # force a rebuild first (after a git pull)
#   MODE=quarterly scripts/run-local.sh reporting
# Each component keeps its own state in out/<component>/, the same layout as the
# S3 bucket, so scripts/pull-cloud-state.sh can seed it from a cloud deployment.
set -euo pipefail
cd "$(dirname "$0")/.."

# Git Bash on Windows rewrites anything that looks like a POSIX path before docker sees
# it. The -v "host:/app/out" mount below came out as a new empty folder named
# "out/<component>;C", so a run on 2026-11-10 saw no state and built nothing.
# Turning the rewrite off is harmless on macOS and Linux, where the variable means nothing.
export MSYS_NO_PATHCONV=1

COMPONENT="${1:?usage: scripts/run-local.sh <component> [--build]}"
IMAGE=cti-pipeline:local
[ -f .env ] || { echo "missing .env: copy .env.example to .env and fill it in"; exit 2; }
[ -d "components/$COMPONENT" ] || { echo "unknown component: $COMPONENT"; ls components; exit 2; }

if [ "${2:-}" = "--build" ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -f deploy/Dockerfile -t "$IMAGE" .
fi

mkdir -p "out/$COMPONENT"
# One-off overrides from the shell win over .env, e.g. SKIP_SCAN=1 to build only.
EXTRA=()
for name in SKIP_SCAN BUILD_PASSES REVIEW REVIEW_ALL REVIEW_MODEL; do
  [ -n "${!name:-}" ] && EXTRA+=(-e "$name=${!name}")
done
docker run --rm --env-file .env \
  -e COMPONENT="$COMPONENT" -e MODE="${MODE:-weekly}" -e CLOUD=local ${EXTRA[@]+"${EXTRA[@]}"} \
  -v "$PWD/out/$COMPONENT:/app/out" "$IMAGE"
echo "output: out/$COMPONENT/"
