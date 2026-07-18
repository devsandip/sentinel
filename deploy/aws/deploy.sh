#!/usr/bin/env bash
# Deploy Sentinel to AWS Elastic Beanstalk (single instance, HTTP).
#
#   AWS_PROFILE=admin ./deploy/aws/deploy.sh
#
# Zips a minimal runtime bundle, uploads it to an S3 deploy bucket, and
# creates/updates the CloudFormation stack that provisions the EB app + env
# and the IAM roles it needs. Idempotent: re-running ships new code.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK="sentinel-eb"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Guard: prod installs from requirements.txt (a uv export), NOT pyproject/uv.lock.
# If that export drifts from the lock, a dependency added in code but missing from
# requirements.txt ships a bundle that imports a module the instance never installed,
# and the app crashes on first render while health still returns 200. This exact drift
# took prod down once. Regenerate from the lock and refuse to deploy on any mismatch.
# Header comments (the "# via" body lines stay) differ only in the --output-file arg,
# so strip column-0 comment lines before comparing.
echo "==> Checking requirements.txt is in sync with uv.lock"
if command -v uv >/dev/null 2>&1; then
  GEN="$(uv export --no-hashes --no-dev --extra pgvector --extra live 2>/dev/null | grep -v '^#')"
  CUR="$(grep -v '^#' requirements.txt)"
  if [ "$GEN" != "$CUR" ]; then
    echo "!! requirements.txt is OUT OF SYNC with uv.lock. Aborting before touching AWS." >&2
    echo "   Prod pip-installs requirements.txt, so a stale export ships the wrong deps." >&2
    echo "   Drift (< committed requirements.txt, > uv.lock):" >&2
    diff <(echo "$CUR") <(echo "$GEN") | sed 's/^/     /' >&2 || true
    echo "" >&2
    echo "   Regenerate, commit, then re-run this deploy:" >&2
    echo "     uv export --no-hashes --no-dev --extra pgvector --extra live --output-file requirements.txt" >&2
    echo "     git add requirements.txt && git commit -m 'chore(deps): sync requirements.txt with uv.lock'" >&2
    exit 1
  fi
  echo "    in sync."
else
  echo "    WARNING: uv not found; cannot verify requirements.txt against the lock. Proceeding." >&2
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="sentinel-eb-deploy-${ACCOUNT_ID}-${REGION}"
STAMP="$(date +%Y%m%d-%H%M%S)"
KEY="bundles/sentinel-${STAMP}.zip"
ZIP="$(mktemp -d)/sentinel-${STAMP}.zip"

echo "==> Building source bundle: $ZIP"
# Include only what the app needs at runtime. Hidden dirs (.platform, .streamlit,
# .ebextensions) are explicit because zip's default globs skip dotfiles.
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

# Live-LLM narration key: read from the gitignored .env (or the environment),
# passed as a NoEcho CFN parameter so it is never committed and never printed.
# Empty disables live mode (the app falls back to scripted).
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"
if [ -z "$ANTHROPIC_KEY" ] && [ -f "$REPO_ROOT/.env" ]; then
  ANTHROPIC_KEY="$(grep -E '^ANTHROPIC_API_KEY=' "$REPO_ROOT/.env" | head -1 | cut -d= -f2-)"
fi
if [ -n "$ANTHROPIC_KEY" ]; then
  echo "    live-LLM: key present (masked); live narration ENABLED behind the cap"
else
  echo "    live-LLM: no key; prod stays scripted-only"
fi

echo "==> Deploying CloudFormation stack: $STACK"
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file deploy/aws/sentinel-eb.yaml \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    SourceBucket="$BUCKET" SourceKey="$KEY" AnthropicApiKey="$ANTHROPIC_KEY"

echo "==> Waiting for the environment to go green..."
aws elasticbeanstalk wait environment-updated \
  --application-name sentinel --environment-name sentinel-prod --region "$REGION" 2>/dev/null || true

CNAME="$(aws elasticbeanstalk describe-environments \
  --application-name sentinel --environment-names sentinel-prod \
  --region "$REGION" --query 'Environments[0].CNAME' --output text)"
HEALTH="$(aws elasticbeanstalk describe-environments \
  --application-name sentinel --environment-names sentinel-prod \
  --region "$REGION" --query 'Environments[0].Health' --output text)"

echo ""
echo "==> Done. Health: $HEALTH"
echo "    URL: http://${CNAME}"
