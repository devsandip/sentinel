# The page that kept no record

2026-07-21 19:07. Previous: [2026-07-21-0128-a-fixture-more-generous-than-prod.md](2026-07-21-0128-a-fixture-more-generous-than-prod.md)

The Sentinel case study went up on sandip.dev today. Description, architecture, build versus buy, a system diagram, and a slot held open for the walkthrough. The video is recorded and published now, so the slot is filled: `c7pvcOekoXk`, embedded through youtube-nocookie. The page source of truth lives in this repo at `docs/portfolio/` and the rendered page lives in the sandip.dev repo, which is a split I would not choose again from scratch but is right given the site is static and this repo is the thing being described.

Two small corrections went in on top. The diagram had no background, so it inherited whatever sat behind it; it now paints an opaque rect that still tracks the palette switcher. And the copy carried em-dashes in the module list, against a standing rule, so those are commas and colons now.

The more useful artifact is `docs/portfolio/CLAUDE.md`, which is build instructions rather than description. It exists because the page took three layout traps to get right and every one of them is invisible in the finished result: the full-bleed maths that has to be computed from the prose column's left edge rather than `translateX(-50%)`, the `1fr` grid track whose `auto` floor held a 680px column open inside a 335px phone, and the sticky rail that paints over anything breaking out of the prose box. None of those are discoverable by reading the CSS. All three are one rebuild away from being rediscovered the hard way.

Then Sandip asked the question this entry is actually about. Has anyone visited?

I could not answer it. Not "the number is low", not "I need an hour". The record did not exist.

Three sources, all lossy, in descending order of usefulness. CloudFront publishes request counts to CloudWatch for free, retained fifteen months, so I have daily totals back to the distribution's creation on 13 July: 881, 1146, 142, 22, 159, 379, 291, 2926, 141. That is requests, not people. Streamlit polls constantly and one visit emits hundreds of lines, so the numbers are unreadable as traffic. The 20 July spike of 2926 is a redeploy day and is mostly me.

The second source is the nginx log on the instance, and Elastic Beanstalk will hand back a tail of it, meaning the last hundred lines, which was about seven hours. In that window: nine Streamlit WebSocket sessions from one Jio IPv6 address, which is me, and exactly one from an Airtel address on a Mac that opened `/_stcore/stream` and pulled the favicon. One real visitor, found by accident, in a seven-hour window I only have because I asked today. The rest of the log is the background every public IP receives: `POST /cgi-bin/` path-traversal attempts, `/wp-json`, `/geoserver/web/`, zgrab probes, raw TLS handshakes logged as garbage URIs. ClaudeBot fetching robots.txt and sitemap.xml.

The third source would have been the app's own audit trail, which is the funny part. Sentinel writes every run to `runtime/audit/<run_id>.jsonl`. That directory is gitignored, wiped on every deploy, and the instance is not SSM-managed, so there is no shell to read it with. The build whose entire argument is that a run must be explicable afterwards to someone who did not run it keeps no durable record of its own runs.

So: **the surface making the argument was the one thing in the system with no audit trail.** I did not notice for eight days because nobody asked.

The fix is CloudFront standard logging, which was always one property on the distribution and had simply never been set. It writes to an S3 bucket the stack now owns, ninety-day lifecycle, cookies excluded, `DeletionPolicy: Retain` so tearing down the stack does not take the record with it. One non-obvious thing worth writing down, because it fails silently rather than loudly: legacy standard logging delivers via a bucket ACL, so `BlockPublicAcls` has to stay false or CloudFront cannot grant itself delivery and simply never writes. The other three public-access blocks are what keep the bucket private.

Logs alone would not have answered the question either, so there is a `traffic-report.sh` beside them. It counts `/_stcore/stream` opens rather than requests, because that endpoint is the WebSocket and there is one per browser tab that actually loaded the app, which makes it the only line in the file that means a person. It strips the scanner background and prints how much of it there was, so the noise is visible as noise rather than quietly discarded. Referrers are in there too, which is the part that matters now that a page exists to refer traffic.

I could not test it against real logs, since delivery lags up to an hour and the bucket was empty. So I tested the parser against a synthetic log with a known answer instead of shipping it unrun. Same instinct as the model-card fixture from this morning, arrived at from the opposite direction: that test was too generous to fail, this one had no data at all, and in both cases the honest move is to construct the input rather than assume the shape.

The permanent cost is that instrumentation is not retroactive. Whoever visited between 13 and 21 July is unknowable, forever, and no amount of care from here recovers it. The single Airtel session in a log tail is all I will ever have of the first eight days. **Turning on the record is cheap; the window before you turned it on is not recoverable at any price.** That is an argument for instrumenting a public surface on the day it goes public, not on the day someone asks how it is doing.

Prod is untouched. The distribution took a config update and nothing else changed.
