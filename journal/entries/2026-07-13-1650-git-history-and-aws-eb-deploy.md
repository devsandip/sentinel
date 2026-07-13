# Git history lands and Sentinel goes live on AWS

2026-07-13 16:50 IST

Previous: [2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md](2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md)

Two things happened today. The build got a real git history, and the app went
live on AWS.

## Git history

The whole P1 through P7 build had been sitting uncommitted. I turned it into a
clean per-phase history: scaffold, P1 ML core, P2 model card, P3 harness, P4
agents and orchestrator, P6 UI, P7 deliverables, the pyarrow fix, then the
process docs. Nine commits that read like the build story. Nothing secret or
generated got tracked. Renamed master to main.

The repo is public at https://github.com/devsandip/sentinel.

## AWS deploy

Chose Elastic Beanstalk over the earlier Render/Fly idea. Reasoning: the app is
a long-running Python server that holds a WebSocket per session, so it needs a
persistent host. Amplify was floated and ruled out. Amplify Hosting only runs
JavaScript frontends (static, SPA, or Node SSR), not a Python Streamlit server.
EB is the lightest managed thing that runs a persistent server.

The shape: single-instance t3.small, HTTP only, no load balancer. Cheapest that
works, about 15 dollars a month. HTTPS and a custom domain are a deliberate
later step (add an ALB and an ACM cert, which flips it to load-balanced at about
28 dollars a month). The whole thing is a CloudFormation stack plus a deploy
script that bundles, uploads to S3, and ships. Redeploy is one command.

First deploy came up Red. The cause was my own nginx override. I had written a
full .platform/nginx/nginx.conf to force WebSocket upgrade headers, and it failed
nginx -t during EB's proxy staging. The app itself booted fine on 8501. The
override was both broken and unnecessary. EB's default Amazon Linux 2023 nginx
already forwards the upgrade headers. I dropped the override, redeployed, and it
went Green.

Then I verified the thing that matters. Health returns ok, the root page renders,
and a raw WebSocket handshake against /_stcore/stream returns 101 Switching
Protocols through nginx. Loaded it in a browser and the full UI paints. So the
WebSocket is real, not assumed.

## What this changes

The project is no longer just a local build. It is committed, public, and running
on a URL. The credibility artifact now has a link.

Live: http://sentinel-prod.eba-ik6jervr.us-east-1.elasticbeanstalk.com
