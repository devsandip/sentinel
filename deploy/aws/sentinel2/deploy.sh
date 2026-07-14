#!/usr/bin/env bash
# Deploy Sentinel 2 to its OWN Elastic Beanstalk stack (single instance, HTTP).
#
#   AWS_PROFILE=admin ./deploy/aws/sentinel2/deploy.sh
#
# A fully independent copy of the prod deploy: distinct CFN stack (sentinel2-eb),
# EB application (sentinel2) + environment (sentinel2-prod), and S3 bundle
# bucket. It shares NO mutable resource with the sentinel.sandip.dev prod stack,
# so running this can never change prod. Idempotent: re-running ships new code.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK="sentinel2-eb"
APP="sentinel2"
ENVNAME="sentinel2-prod"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="sentinel2-eb-deploy-${ACCOUNT_ID}-${REGION}"
STAMP="$(date +%Y%m%d-%H%M%S)"
KEY="bundles/sentinel2-${STAMP}.zip"
ZIP="$(mktemp -d)/sentinel2-${STAMP}.zip"

echo "==> Building source bundle: $ZIP"
zip -r -q "$ZIP" \
  app.py Procfile requirements.txt pyproject.toml \
  sentinel \
  .platform .streamlit \
  -x '*/__pycache__/*' '*.pyc' '**/.DS_Store'
echo "    bundle contents:"
unzip -l "$ZIP" | awk 'NR>3 {print "      "$4}' | grep -vE '^\s*$' | head -40

echo "==> Ensuring deploy bucket: s3://$BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  aws s3api put-bucket-encryption --bucket "$BUCKET" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

echo "==> Uploading bundle to s3://$BUCKET/$KEY"
aws s3 cp "$ZIP" "s3://$BUCKET/$KEY" >/dev/null

# Live-LLM narration key: optional. sentinel2 defaults to scripted-only (free).
# If a key is present in the environment or the gitignored .env, live mode is
# enabled behind the same cumulative cap. Comment out to force scripted-only.
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"
if [ -z "$ANTHROPIC_KEY" ] && [ -f "$REPO_ROOT/.env" ]; then
  ANTHROPIC_KEY="$(grep -E '^ANTHROPIC_API_KEY=' "$REPO_ROOT/.env" | head -1 | cut -d= -f2-)"
fi
if [ -n "$ANTHROPIC_KEY" ]; then
  echo "    live-LLM: key present (masked); live narration ENABLED behind the cap"
else
  echo "    live-LLM: no key; sentinel2 stays scripted-only"
fi

echo "==> Deploying CloudFormation stack: $STACK"
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file deploy/aws/sentinel2/sentinel2-eb.yaml \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    SourceBucket="$BUCKET" SourceKey="$KEY" AnthropicApiKey="$ANTHROPIC_KEY"

echo "==> Waiting for the environment to go green..."
aws elasticbeanstalk wait environment-updated \
  --application-name "$APP" --environment-name "$ENVNAME" --region "$REGION" 2>/dev/null || true

CNAME="$(aws elasticbeanstalk describe-environments \
  --application-name "$APP" --environment-names "$ENVNAME" \
  --region "$REGION" --query 'Environments[0].CNAME' --output text)"
HEALTH="$(aws elasticbeanstalk describe-environments \
  --application-name "$APP" --environment-names "$ENVNAME" \
  --region "$REGION" --query 'Environments[0].Health' --output text)"

echo ""
echo "==> Done. Health: $HEALTH"
echo "    URL: http://${CNAME}"
echo "    Next: AWS_PROFILE=admin ./deploy/aws/sentinel2/enable-https.sh"
