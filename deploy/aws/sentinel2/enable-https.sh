#!/usr/bin/env bash
# Put HTTPS in front of the Sentinel 2 EB demo on sentinel2.sandip.dev.
#
#   AWS_PROFILE=admin ./deploy/aws/sentinel2/enable-https.sh
#
# Requests (or reuses) an ACM cert for sentinel2.sandip.dev, auto-creates its DNS
# validation record in the shared sandip.dev hosted zone (a NEW record; the
# existing sentinel.sandip.dev records are never touched), waits for ISSUED, then
# deploys its OWN CloudFront distribution + Route 53 alias in a distinct CFN
# stack (sentinel2-https). Reuses the prod HTTPS template unchanged, since it is
# fully parameterized. Idempotent: safe to re-run.
set -euo pipefail

REGION="us-east-1"                 # CloudFront certs must live in us-east-1
DOMAIN="sentinel2.sandip.dev"
ZONE_ID="Z09218533I2UQLLSE7RP4"    # sandip.dev hosted zone (shared; add-only)
STACK="sentinel2-https"
APP="sentinel2"
ENVNAME="sentinel2-prod"
TEMPLATE="deploy/aws/sentinel-https.yaml"   # parameterized; reused as-is
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

ORIGIN="$(aws elasticbeanstalk describe-environments \
  --application-name "$APP" --environment-names "$ENVNAME" \
  --region "$REGION" --query 'Environments[0].CNAME' --output text)"
echo "==> EB origin: $ORIGIN"

# --- 1. Find or request the ACM cert --------------------------------------
CERT_ARN="$(aws acm list-certificates --region "$REGION" \
  --query "CertificateSummaryList[?DomainName=='${DOMAIN}' && Status!='FAILED'].CertificateArn | [0]" \
  --output text)"

if [ "$CERT_ARN" = "None" ] || [ -z "$CERT_ARN" ]; then
  echo "==> Requesting ACM cert for $DOMAIN"
  CERT_ARN="$(aws acm request-certificate --region "$REGION" \
    --domain-name "$DOMAIN" --validation-method DNS \
    --query CertificateArn --output text)"
  until aws acm describe-certificate --region "$REGION" --certificate-arn "$CERT_ARN" \
        --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' \
        --output text 2>/dev/null | grep -q .; do sleep 3; done
else
  echo "==> Reusing existing cert: $CERT_ARN"
fi
echo "    cert: $CERT_ARN"

# --- 2. Ensure the DNS validation record exists ---------------------------
STATUS="$(aws acm describe-certificate --region "$REGION" --certificate-arn "$CERT_ARN" \
  --query 'Certificate.Status' --output text)"
if [ "$STATUS" != "ISSUED" ]; then
  VN="$(aws acm describe-certificate --region "$REGION" --certificate-arn "$CERT_ARN" \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' --output text)"
  VV="$(aws acm describe-certificate --region "$REGION" --certificate-arn "$CERT_ARN" \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Value' --output text)"
  echo "==> Upserting DNS validation record: $VN"
  aws route53 change-resource-record-sets --hosted-zone-id "$ZONE_ID" \
    --change-batch "{\"Changes\":[{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"$VN\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$VV\"}]}}]}" \
    >/dev/null
  echo "==> Waiting for the cert to validate (can take a few minutes)..."
  aws acm wait certificate-validated --region "$REGION" --certificate-arn "$CERT_ARN"
fi
echo "==> Cert ISSUED."

# --- 3. Deploy CloudFront + Route 53 alias --------------------------------
echo "==> Deploying CloudFront stack: $STACK (distribution rollout takes ~5-15 min)"
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --region "$REGION" \
  --parameter-overrides \
    CertificateArn="$CERT_ARN" \
    OriginDomainName="$ORIGIN" \
    DomainName="$DOMAIN" \
    HostedZoneId="$ZONE_ID"

CF_DOMAIN="$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue | [0]" --output text)"

echo ""
echo "==> Done."
echo "    HTTPS URL: https://${DOMAIN}"
echo "    CloudFront: ${CF_DOMAIN}"
echo "    (DNS + edge propagation may take a few more minutes on first deploy.)"
