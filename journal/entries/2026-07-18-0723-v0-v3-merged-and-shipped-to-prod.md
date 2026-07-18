# v0 through v3 are merged to main and shipped to prod.

Date: 2026-07-18 07:23
Previous: [2026-07-17-2332-v2-and-v3-built-and-verified.md](2026-07-17-2332-v2-and-v3-built-and-verified.md)

The governed-codegen build is no longer on a branch. Both PRs are merged and the
whole of v0 through v3 is live on the public link.

The merge was stacked and went in order. PR #1, v0 and v1, merged into main first
as a merge commit. PR #2, v2 and v3, was based on the first branch, so I retargeted
its base to main once the first landed, then merged it. main now carries both merge
commits, caa9228 under 4692c7c, and every feature commit beneath them. The two
feature branches are deleted on GitHub and locally. Nothing is lost, because the
commits they pointed at are reachable from main, and git confirmed both branches
were fully merged before it removed them. Local main is fast-forwarded and in sync.

Then I deployed. This is the first time any of v0 through v3 has left my machine.
Prod ran 9dcd20b since 2026-07-14, the platform build that governs scikit-learn. It
now runs 4692c7c, the same platform plus the thing the rethink argued for: the
model writes the analysis code, and a two-parser gate stands between generation and
execution. The deploy is additive, so the public link keeps everything it had and
gains the governed code-generation console, the registry certification lifecycle,
and the evidence pack.

The deploy is verified, not assumed. The Elastic Beanstalk environment is green and
the public health endpoint returns 200 over HTTPS. I confirmed the running version
by its source bundle S3 key, bundles/sentinel-20260718-071819.zip, not by the
version label, because the label is reused and the key is not. Live-LLM narration
stayed enabled: the key was sourced from the main-checkout .env at deploy time, so
the log showed the key present rather than the blank-key fallback that quietly drops
prod to scripted.

What this closes. The rethink from 2026-07-17, govern the LLM and not scikit-learn,
is now the artifact a visitor sees, not a plan in a branch. The old platform demo is
still there underneath, but the front of the argument is the gate. What is still
deliberately out has not changed: the marimo notebook and the Quarto PDF render, and
all of v4, which holds the two forks I will not take alone, OPA externalisation and
the L3 path.
