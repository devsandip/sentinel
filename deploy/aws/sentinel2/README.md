# Sentinel 2 — an isolated second deployment

`sentinel2.sandip.dev` is a fully independent copy of the Sentinel demo, serving
the improved build (guided cold-open, completing human gate, reordered tabs,
hidden Streamlit chrome). It exists so the interview version can evolve without
touching the original at `sentinel.sandip.dev`.

## Why it cannot touch prod

Every resource is separately named. Nothing mutable is shared.

| Concern | sentinel (prod) | sentinel2 |
| --- | --- | --- |
| CFN app stack | `sentinel-eb` | `sentinel2-eb` |
| CFN HTTPS stack | `sentinel-https` | `sentinel2-https` |
| EB application | `sentinel` | `sentinel2` |
| EB environment | `sentinel-prod` | `sentinel2-prod` |
| S3 bundle bucket | `sentinel-eb-deploy-*` | `sentinel2-eb-deploy-*` |
| IAM roles | auto-named per stack | auto-named per stack |
| ACM cert | `sentinel.sandip.dev` | `sentinel2.sandip.dev` |
| CloudFront dist | prod distribution | its own distribution |
| Vector store | pgvector on shared RDS | local (bundled), no RDS |

The one shared thing is the `sandip.dev` Route 53 hosted zone. The sentinel2
HTTPS stack only **adds** records for `sentinel2.sandip.dev` and its ACM
validation name. The existing `sentinel.sandip.dev` records are never read or
modified. CloudFront also enforces that a given alias belongs to one
distribution, so the two domains cannot collide.

Because sentinel2 uses the local vector store (`SENTINEL_VECTOR_STORE=local`),
its instance role has no access to the prod RDS secret or Bedrock. It carries
only the EB web/worker tier policies.

## Deploy

```bash
# 1. App code + EB env (creates the sentinel2-eb stack; ~10-15 min first time)
AWS_PROFILE=admin ./deploy/aws/sentinel2/deploy.sh

# 2. HTTPS front on sentinel2.sandip.dev (ACM + CloudFront; ~10-20 min first time)
AWS_PROFILE=admin ./deploy/aws/sentinel2/enable-https.sh
```

Redeploy app code any time by re-running step 1. Both scripts are idempotent.

## Cost

A second single-instance `t3.small` EB environment is about 15 USD/month, plus
pennies of CloudFront at demo traffic. There is no load balancer and no RDS.

## Teardown

When the interview is done, remove sentinel2 entirely (prod is untouched):

```bash
AWS_PROFILE=admin ./deploy/aws/sentinel2/teardown.sh
```
