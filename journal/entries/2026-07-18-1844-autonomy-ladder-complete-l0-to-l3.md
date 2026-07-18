# The autonomy ladder is complete, L0 to L3

2026-07-18 18:44

Previous: [2026-07-18-1756-v3-outputs-and-v4-access-policy.md](2026-07-18-1756-v3-outputs-and-v4-access-policy.md)

Sandip said finish everything and went away from the keyboard. So I finished the
buildable v4 work and left only the one item that genuinely needs external
infrastructure. The autonomy ladder now has all four rungs working, not one and a
caption.

The flow no longer freezes the tier at L2. It computes it from the persona and the
dataset classification and routes on it. A certified analyst on german_credit
resolves to L2 and the model writes gated code, the same hero path as before. An
uncertified junior analyst, same first-line role, resolves to L1: the model picks
the certified fair-lending analysis and fills typed, bounded parameters, and there
is no code to gate because none was written. A second-line persona resolves to L0
and may not run. To make L1 reachable I added a Junior Analyst persona and gave
the personas attestations, so the same person on the same data lands at a
different autonomy depending on what they have earned.

Then L3, which needed the most new ground. First I onboarded synthetic_its, which
was registered with no onboarder. It generates fully synthetically: a daily metric
with a trend, weekly seasonality, a control series, and a known +12 effect injected
after day 250. Because the effect is injected, the ground truth is known, which is
the point of a validation fixture. It is the only Public-class dataset, so the only
legal home for L3.

The L3 route runs broad code in the sandbox on that data. The governance claim I
wanted to make demonstrable is: at the highest tier the model gets more analytical
rope, but not more safety rope. So the L3 gate widens the allowlist to whole
packages and stdlib compute, while the egress, filesystem, and dynamic-code deny
lists stay exactly as they are at L2. The benign L3 analysis is a real
difference-in-differences estimate that recovers +11.9 (95% CI 11.6 to 12.2)
against the ground truth of +12, and its evidence pack says what it does not say:
this is an association under a parallel-trends assumption, not a proven causal
effect, and the ground-truth comparison is only possible because the data is
synthetic. Three adversarial L3 requests confirm the hard limits hold: exfiltrate
is refused as CTL-EGRESS-01, a file write as CTL-CODE-02, an eval as CTL-CODE-03,
all at L3.

The govflow surface now has a mode toggle, fair lending on german_credit or causal
impact on synthetic_its, so switching dataset recomputes the tier live. The nicest
thing to see is the analyst on synthetic_its: Public data allows L3, but the
analyst has no sandbox waiver, so the tier resolves to L2, min(class L3, person
L2). A permissive dataset does not elevate a person. That is the tier resolver
firing in the UI, not just in a test.

What I did not build, and why. OPA externalisation is the one genuine fork left. It
needs an external policy server the public instance would depend on, it is a PRD
open question, and standing one up while Sandip is away and cannot weigh the
operational cost is his call, not mine. The purpose matrix and the tier resolver
already show the policy logic; externalising it to OPA is an architecture decision
about where that logic runs, not whether it exists.

Five commits on feat/govcodegen-v4 today across two sittings, all pushed, PR #3
open. 316 tests pass, up from 251 at the start of the day. Prod is untouched and
still v0-v3. I did not deploy: prod is public, the last deploy crashed while Sandip
was watching, and shipping a large change blind while he is away is the wrong call.
Everything is green and ready for his review.
