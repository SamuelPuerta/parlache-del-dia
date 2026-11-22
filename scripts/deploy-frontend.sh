#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"
BUCKET=$(terraform output -raw frontend_bucket)
DIST=$(terraform output -raw cloudfront_distribution_id)
cd ../../
aws s3 sync frontend/ "s3://$BUCKET" --delete
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"
