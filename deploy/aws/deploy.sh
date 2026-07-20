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

# Guard: the bundle is built from the working TREE, not from HEAD. `zip` walks the
# filesystem, so what ships is whatever is on disk right now. A checkout can sit on
# exactly origin/main and still hold something else in its index: on 2026-07-20 this
# folder was on main at origin/main with a full revert of three merges staged, 2,699
# deletions, and every check in use at the time passed it. The bundle would have gone
# Green without the Gate read or the Live LLM fix and reported success.
#
# So the check has two clauses and the second is the one that fires: HEAD is an
# ancestor of origin/main (nothing unreviewed ships) AND the tree is clean (what
# ships is what HEAD says). Untracked files count, because a new module under
# sentinel/ is inside the zip's file list and would ship without ever being in git.
#
# Verifiable failure is fatal; inability to verify is a warning, matching the
# requirements guard below. A deploy from a non-git copy is unusual but not wrong.
echo "==> Checking the tree being zipped is what origin/main says it is"
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "    WARNING: not a git checkout; cannot verify what is being shipped. Proceeding." >&2
else
  git fetch --quiet origin main 2>/dev/null \
    || echo "    WARNING: could not fetch origin/main; comparing against the local ref." >&2

  DIRTY="$(git status --porcelain)"
  if [ -n "$DIRTY" ]; then
    echo "!! The working tree is DIRTY. Aborting before touching AWS." >&2
    echo "   deploy.sh zips the tree, so these differences would ship without review:" >&2
    echo "$DIRTY" | sed 's/^/     /' >&2
    echo "" >&2
    echo "   Untracked (??) files count: anything under a zipped path ships too." >&2
    echo "   Commit, stash or clean, then re-run this deploy." >&2
    exit 1
  fi

  if ! git rev-parse --verify --quiet origin/main >/dev/null; then
    echo "    WARNING: no origin/main ref; cannot verify HEAD is merged. Proceeding." >&2
  elif ! git merge-base --is-ancestor HEAD origin/main; then
    echo "!! HEAD is NOT an ancestor of origin/main. Aborting before touching AWS." >&2
    echo "     HEAD        $(git rev-parse --short HEAD) ($(git rev-parse --abbrev-ref HEAD))" >&2
    echo "     origin/main $(git rev-parse --short origin/main)" >&2
    echo "" >&2
    echo "   This checkout holds commits that are not on main. Merge them first," >&2
    echo "   or deploy from a checkout that is on main." >&2
    exit 1
  else
    echo "    clean, and HEAD is on origin/main."
  fi
fi

# Guard: prod installs from requirements.txt (a uv export), NOT pyproject/uv.lock.
# If that export drifts from the lock, a dependency added in code but missing from
# requirements.txt ships a bundle that imports a module the instance never installed,
# and the app crashes on first render while health still returns 200. This exact drift
# took prod down once. Regenerate from the lock and refuse to deploy on any mismatch.
#
# The export command (including which extras ship) is read from requirements.txt's own
# header line, which uv writes when it generates the file. That header is the single
# source of truth: change the extras, regenerate, and this guard follows the new header
# with no flags duplicated here. We strip the --output-file arg (compare against stdout)
# and drop column-0 comment lines so the header itself never counts as drift.
echo "==> Checking requirements.txt is in sync with uv.lock"
REQ_CMD="$(grep -oE 'uv export .*' requirements.txt | head -1 | sed -E 's/ --output-file[= ][^ ]+//')"
if ! command -v uv >/dev/null 2>&1; then
  echo "    WARNING: uv not found; cannot verify requirements.txt against the lock. Proceeding." >&2
elif [ -z "$REQ_CMD" ]; then
  echo "    WARNING: no 'uv export' command in requirements.txt's header; cannot verify. Proceeding." >&2
else
  read -r -a REQ_ARGV <<< "$REQ_CMD"          # split into argv; no word-split/glob surprises
  GEN="$("${REQ_ARGV[@]}" 2>/dev/null | grep -v '^#')"
  CUR="$(grep -v '^#' requirements.txt)"
  if [ "$GEN" != "$CUR" ]; then
    echo "!! requirements.txt is OUT OF SYNC with uv.lock. Aborting before touching AWS." >&2
    echo "   Prod pip-installs requirements.txt, so a stale export ships the wrong deps." >&2
    echo "   Drift (< committed requirements.txt, > uv.lock):" >&2
    diff <(echo "$CUR") <(echo "$GEN") | sed 's/^/     /' >&2 || true
    echo "" >&2
    echo "   Regenerate, commit, then re-run this deploy:" >&2
    echo "     $REQ_CMD --output-file requirements.txt" >&2
    echo "     git add requirements.txt && git commit -m 'chore(deps): sync requirements.txt with uv.lock'" >&2
    exit 1
  fi
  echo "    in sync."
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
