#!/usr/bin/env bash
# Tear down the Sentinel 2 stacks entirely. Prod (sentinel.sandip.dev) is not
# touched: this only deletes sentinel2-* resources.
#
#   AWS_PROFILE=admin ./deploy/aws/sentinel2/teardown.sh
set -euo pipefail

REGION="us-east-1"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="sentinel2-eb-deploy-${ACCOUNT_ID}-${REGION}"

echo "==> Deleting HTTPS stack: sentinel2-https (CloudFront can take ~15 min)"
aws cloudformation delete-stack --stack-name sentinel2-https --region "$REGION"
aws cloudformation wait stack-delete-complete --stack-name sentinel2-https --region "$REGION" || true

echo "==> Deleting EB stack: sentinel2-eb"
aws cloudformation delete-stack --stack-name sentinel2-eb --region "$REGION"
aws cloudformation wait stack-delete-complete --stack-name sentinel2-eb --region "$REGION" || true

echo "==> Emptying and deleting bundle bucket: s3://$BUCKET"
aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" 2>/dev/null || true
aws s3api delete-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null || true

echo ""
echo "==> sentinel2 torn down. The sentinel.sandip.dev stacks were not touched."
echo "    Note: the ACM cert for sentinel2.sandip.dev (if issued) remains; delete"
echo "    it manually from ACM if you want it gone."
