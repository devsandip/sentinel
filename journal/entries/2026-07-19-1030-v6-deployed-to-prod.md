# v6 is live: the unified app is what prod serves now

2026-07-19 10:30. Previous: [2026-07-19-1011-unified-app-shell-datasets-history.md](2026-07-19-1011-unified-app-shell-datasets-history.md)

Sandip said merge and deploy, and gave the approval for the two gated commands. So v6 shipped.

PR #5 merged clean to main (`2e47fce`). I pulled it into the main checkout, ran the suite there (374 passed, 2 skipped), and deployed: bundle `sentinel-20260719-101916.zip`, CloudFormation changeset applied, EB Ready and Green, live-LLM enabled behind the cap. Prod moved v5 to v6.

Then I verified it the way this project verifies deploys, not by a health probe. I loaded `sentinel.sandip.dev` and the login persona gate rendered, which is the tell: that screen did not exist in v5. I picked Data Scientist and landed on the command center, with the four live tiles reading real numbers (Datasets 8, Registry 3 as 1 certified / 1 candidate / 1 refused, Adoption 19) and the grouped sidebar showing live counts. Then I ran a governed flow on the instance. Run `7d306d5dfb64` completed all nine stages at tier L2 with 3 controls fired, and the Access stage showed the policy-scoped view built by construction: 6 granted columns of 21, the rest withheld by data minimisation. That is the whole v6 surface working live, not a page that merely loads.

One bookkeeping note. `describe-application-versions` returned null for the source-bundle key, because CloudFormation manages the application version under a generated label, not the bundle filename. The deploy script's own upload log plus the successful changeset are the provenance for the bundle. Not a problem, just not where I first looked.

What is left is small and known. The W29 weekly summary is due Monday. Dark mode, RBAC-gated navigation, the B-style contextual drawers, and OPA externalisation are all still deferred and still Sandip's call. Nothing about the deploy opened a new question.
