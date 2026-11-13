#!/usr/bin/env bash
# One-time copy of a cloud deployment's state into out/, so local runs continue where
# the cloud left off (dedup log, registers, IDs, earlier deliverables) instead of
# re-reporting everything as new. Read only on the AWS side; needs the AWS CLI and
# credentials that can read the output bucket.
#   scripts/pull-cloud-state.sh my-bucket
#   COMPANY=acme scripts/pull-cloud-state.sh my-bucket   # another company's state
#
# The AWS deployment this defaulted to was torn down on 2026-10-06, bucket included, so
# there is no default any more: pass the bucket of a live deployment, or seed from a zip
# export instead (docs/local-setup.md step 4).
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${1:-}"
COMPANY="${COMPANY:-genelabs}"
# The layouts the entrypoint writes: GeneLabs at the bucket root, others under a prefix.
if [ "$COMPANY" = "genelabs" ]; then SRC=""; DEST="out"; else SRC="companies/$COMPANY/"; DEST="data/companies/$COMPANY/out"; fi
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
  aws s3 sync "s3://$BUCKET/$SRC$c/" "$DEST/$c/" --only-show-errors
done
echo "state copied into $DEST/"
