#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"
ADMIN=$(terraform output -raw admin_bucket)
cd ../../
aws s3 cp backend/data/words.json "s3://$ADMIN/imports/words.json"
