# HTTPS lands on a custom domain

2026-07-13 17:20 IST

Previous: [2026-07-13-1650-git-history-and-aws-eb-deploy.md](2026-07-13-1650-git-history-and-aws-eb-deploy.md)

The deploy entry from half an hour ago called HTTPS a later step. It got done.

The trigger was real. Chrome refused to open the http-only EB URL. It silently
upgrades http to https, hit port 443 which the single-instance env does not open,
and timed out. My curl and the in-app browser used plain http, so they worked and
I had missed it. The lesson: a link that works for me is not a link that works
for the person I hand it to.

The fix had a constraint. You cannot put a trusted cert on the raw
elasticbeanstalk.com URL, because AWS owns that domain and no CA will validate it.
HTTPS needs a domain I control. Chose sentinel.sandip.dev.

The shape: CloudFront in front of the existing EB instance. CloudFront terminates
TLS with an ACM cert and forwards to EB over http, passing the WebSocket through
(caching disabled, all viewer headers forwarded). This kept EB single-instance
and cheap. CloudFront is pennies at demo traffic, so the bill is still about 15
dollars a month. The alternative, flipping EB to load-balanced with an ALB, would
have cost more and bought nothing here.

All of it is Route 53 native, so it automated cleanly: request the ACM cert,
write the DNS validation record, wait for issue, deploy the CloudFront stack, add
the alias. One script, one template.

One verification wrinkle worth remembering. My first WebSocket probe over HTTPS
returned 200, not 101. The cause was curl negotiating HTTP/2 with CloudFront, and
the Upgrade handshake is an HTTP/1.1 mechanism. Forcing HTTP/1.1 returned 101,
which is what browsers actually do for the WebSocket connection. Then I loaded the
page in a browser and the full UI painted, which is the real proof.

Live: https://sentinel.sandip.dev
