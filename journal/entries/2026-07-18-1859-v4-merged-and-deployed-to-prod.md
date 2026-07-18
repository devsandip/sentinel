# v4 merged to main and deployed to prod

2026-07-18 18:59

Previous: [2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md](entries/2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md)

Sandip came back and said merge and deploy. So I did both, and this time I
verified the deploy the way the last one should have been verified: by loading a
page and running a flow, not by trusting health 200.

PR #3 merged into main as `3b17921`, the eight-commit v4 branch. The remote and
local feature branches are gone. main now carries the full autonomy ladder, the
purpose matrix, the tier resolver, and the two v3 secondary outputs.

The deploy went clean. requirements.txt had no drift from uv.lock, so the guard
passed and there was no repeat of the missing-deps crash; v4 added no new runtime
dependencies (marimo is not a dependency, statistics and math are stdlib,
everything else was already there). The bundle
`bundles/sentinel-20260718-185231.zip` built from main, CloudFormation updated,
the environment went green. The live-LLM key was present at deploy time, read from
the main-checkout .env, so narration stays on behind the cap.

Then the verification that matters. https://sentinel.sandip.dev returns 200 over
HTTPS and the http URL 301-redirects, but that is the necessary-not-sufficient
part. I loaded the page and it rendered. I opened Governed code generation and the
new surfaces are all there on the instance: the analysis-mode toggle (fair lending
on german_credit, causal impact on synthetic_its), the computed tier chip that
reads "resolves to L2 = min(class L2, person L2)", the Access-policy section, and
the full purpose matrix with every dataset and the CTL-PURP-01 showpiece. Then I
ran a governed analysis. Run 696ef64456bc completed on the instance: all nine
stages green through Attest, CTL-DISC-02 suppressing the n=6 band, CTL-PROXY-01
flagging the proxy, and a narration built from the screened numbers. Execute
passing means the subprocess sandbox ran generated code on the box, which is the
part a health probe can never tell you.

So prod is v4 now, verified rendering and running, not just answering a probe.
Deployed bundle `sentinel-20260718-185231.zip`, EB green, live-LLM on. main is at
the merge commit `3b17921`. The one thing still deferred is OPA externalisation,
which needs an external server and is Sandip's architecture call. The weekly
journal summaries for W28 and W29 are still owed.
