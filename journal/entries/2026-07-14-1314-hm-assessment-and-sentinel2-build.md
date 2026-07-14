# 2026-07-14 13:14 — HM assessment, cold-open fixes, and an isolated sentinel2

Previous: [2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md](2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md)

Today I stopped adding features and asked the harder question. When the Citi
hiring manager opens the link cold, with no one there to explain it, does
Sentinel land in two minutes? I ran a structured evaluation from his chair:
several lenses, a full role-play of him clicking through, and an adversarial
critic over the lot. I wrote the findings up as an HTML deck.

The verdict was lean-yes. The artifact does the job it needs to do. It kills the
"does not know fintech or governance" doubt and proves I can build. It does not,
by itself, close the data-science-depth or product-altitude questions, and it is
not meant to. Its job is to earn the next conversation, and it does.

But the cold open leaks in four places. The "so what" was off-screen, sitting in
PRODUCT_BRIEF.md, which a cold visitor never opens. The human gate dead-ended:
the default persona was the Analyst, who cannot approve, so a first Approve click
looked broken and hid the model card behind it. Sixteen destinations with no
"start here." And the deliberately-simple model read as thin, because the reason
for it was never on the screen.

The sharpest note came from the critic: you cannot fix an altitude problem caused
by too much surface by adding more surface. So the move is to subtract in the app
and put the strategy in the note, which is the one surface the reader is
guaranteed to open.

I implemented the fixes on this branch, which becomes a second site, not prod.
The UI now starts as the MRM Approver, so a naive Run then Approve completes end
to end and reaches the model card. Segregation of duties is still there to see by
switching to the Analyst, with a visible denial and a one-click recovery. There
is a thesis line and a 60-second guided path on the landing, a "what to notice"
strip after a run, the payoff tabs (Fairness, Model Card, Audit Log) now lead, a
"baseline by design" line on Results, and the Streamlit chrome is hidden. I
verified the cold path in a browser: it completes. 127 tests still pass, ruff
clean.

The deployment decision: I am not touching sentinel.sandip.dev. The improved
build goes to a separate sentinel2.sandip.dev on a fully parallel stack. New
CloudFormation stacks, EB application and environment, S3 bucket, IAM roles,
certificate, and CloudFront distribution. The one shared thing is the DNS zone,
where the new stack only adds a record. sentinel2 runs the local TF-IDF vector
store, so it does not touch prod's RDS at all. The deploy scripts live under
deploy/aws/sentinel2/ with a teardown. Prod's deploy files are unchanged, and I
checked that with git.

sentinel2 is not provisioned yet. It is a second always-on t3.small at about 15
dollars a month, so provisioning waits on a go-ahead. Everything runs locally in
the meantime with `./run.sh`, on the same code and vector store sentinel2 will
serve.
