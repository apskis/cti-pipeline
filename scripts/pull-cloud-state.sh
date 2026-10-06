#!/usr/bin/env bash
# One-time copy of a cloud deployment's state into out/, so local runs continue where
# the cloud left off (dedup log, registers, IDs, earlier deliverables) instead of
# re-reporting everything as new. Read only on the AWS side; needs the AWS CLI and
# credentials that can read the output bucket.
#   scripts/pull-cloud-state.sh my-bucket
#
# The AWS deployment this defaulted to was torn down on 2026-10-06, bucket included, so
# there is no default any more: pass the bucket of a live deployment, or seed from a zip
# export instead (docs/local-setup.md step 4).
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${1:-}"
[ -n "$BUCKET" ] || {
  echo "usage: scripts/pull-cloud-state.sh <bucket>"
  echo
  echo "No default bucket: the cti-pipeline-out-574625227402 deployment was deleted."
  echo "To seed from a zip export instead, see docs/local-setup.md step 4."
  exit 2
}
for c in components/*/; do
  c="$(basename "$c")"
  echo "== $c"
  aws s3 sync "s3://$BUCKET/$c/" "out/$c/" --only-show-errors
done
echo "state copied into out/"
