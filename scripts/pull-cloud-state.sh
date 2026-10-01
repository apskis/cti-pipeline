#!/usr/bin/env bash
# One-time copy of a cloud deployment's state into out/, so local runs continue where
# the cloud left off (dedup log, registers, IDs, earlier deliverables) instead of
# re-reporting everything as new. Read only on the AWS side; needs the AWS CLI and
# credentials that can read the output bucket.
#   scripts/pull-cloud-state.sh                       # default bucket
#   scripts/pull-cloud-state.sh my-other-bucket
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${1:-cti-pipeline-out-574625227402}"
for c in components/*/; do
  c="$(basename "$c")"
  echo "== $c"
  aws s3 sync "s3://$BUCKET/$c/" "out/$c/" --only-show-errors
done
echo "state copied into out/"
