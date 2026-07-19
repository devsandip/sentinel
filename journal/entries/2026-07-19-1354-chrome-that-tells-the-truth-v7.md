# Chrome that tells the truth, and v7 in prod

2026-07-19 13:54. Previous: [2026-07-19-1030-v6-deployed-to-prod.md](2026-07-19-1030-v6-deployed-to-prod.md)

Today's work was all chrome, and it turned out to have a single theme. The app shell was claiming things the page could not back up.

Three fixes shipped across two PRs, both merged, both now in prod.

PR #8 was identity. The persona lived in two places, the sidebar block and the header, and the header also carried a Tier chip and a decorative green governed badge that was on whether or not anything was governed. Identity is now one surface, the header's Acting as popover. The tier left the global bar because a tier is run-scope and belongs in the Run flow. The governed badge only appears as a warning, when a control is toggled off. A badge that is always green says nothing. The sidebar also got Material icons and an in-app Back control, so leaving a screen no longer means leaving Sentinel.

PR #9 was two things. First, the Data and Purpose chips. They described a run but rendered on every screen with a hardcoded german_credit and fair-lending fallback, so the dashboard and all four catalog screens announced a data scope and a purpose that nothing on the page had. Chips are now run-scoped: the Run walkthrough takes them from the published run, else the draft config; the credit pipeline shows Data only once a run exists, because an orchestrator run carries no declared purpose and I would rather show one chip than invent the second. Everywhere else shows none. Second, the sidebar rhythm. Sandip said it was way too much space and he was right. Streamlit puts a 16px gap between every block element, so each nav row carried 16px on top of its own padding and an eight-item rail ran 590px tall. The mockup's own sidenav stacks rows flush and buys air only at the group boundary. Matched it. The rail is 410px now for the same eight items.

Then deployed. Bundle `sentinel-20260719-133917.zip`, CloudFormation applied, EB Ready and Green, live-LLM on. Verified by loading the site and clicking through it, not by a probe: Overview renders with no context chips, Run shows Data german_credit RESTRICTED plus Purpose fair lending review, the rail is the tight version, and a nav click reruns the script, which is the proof the WebSocket session is live.

Four things worth remembering, all cheap to relearn the hard way.

Streamlit's `st.button(icon=...)` wraps the icon and label in an inner flex div that centers by default. Setting the button to flex-start does nothing. The rule has to target `button > div`. That one cost a diagnostic round trip.

The header renders above the body, so on the frame a run starts, the topbar has already drawn with the pre-run scope. The pipeline's Run handler now reruns after starting the run. The run is already in the orchestrator, so the rerun is cheap.

The dev server runs with the file watcher off, so a browser reload does not pick up an edit. The server has to be restarted. I lost a screenshot to this before noticing the stale copy in it.

And a false negative worth writing down: the WebSocket curl check returns 200 through CloudFront but 101 direct to the EB origin. The origin is correct. CloudFront does not complete a synthetic handshake from a headers-only curl. The browser session connects fine, which the live rerun proved. If that check is ever used as a smoke test, point it at the EB CNAME, not the CDN.

Docs moved with the code. ui-spec 2.1 now records that the chips are run-scoped and why, and 2.2 records the as-built rail: 222px, this rhythm, Material icons at 16px, the sticky Back with its rule. The spec still described the 238px inline-SVG mockup.

One correction to make in my own notes. Earlier in this session I described OPA externalisation as killed. That is not backed by anything. No commit, no doc, no decision from Sandip. It remains what the W29 summary says it is: the one deferred item explicitly waiting on his call. The branch this work landed on is named for OPA scope, which is probably where I picked the idea up. Recording it here so the mistake does not propagate.

What is left is unchanged and small. OPA externalisation waits on Sandip. Dark mode, RBAC-gated navigation, and the B-style contextual drawers are deferred by choice. Drift monitoring still has no stage in the lifecycle. The SR 11-7 retrieval still ranks the internal modeling standard above SR 11-7 itself. And app.py keeps growing with a hand-rolled router; the noted fix is Streamlit's own multipage support.
