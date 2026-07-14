# Live-LLM narration goes live in prod

Date: 2026-07-14 06:46
Previous: [2026-07-13-2237-analysis-platform-and-pgvector-prod.md](2026-07-13-2237-analysis-platform-and-pgvector-prod.md)

Live-LLM narration works now, and it is on the public URL. Until tonight it
never actually ran.

The bug was quiet. The gateway imports the Anthropic SDK lazily and wraps the
call in a try/except that falls back to scripted narration on any failure. The
SDK was never installed and never declared as a dependency, so every live call
raised ModuleNotFoundError, fell back, and looked like scripted output. The demo
had a Live LLM toggle that did nothing, and the fallback hid it. I found it by
actually inspecting the fallback reason instead of trusting the toggle.

The fix is small: an optional `live` extra (anthropic), lazily imported so
scripted mode still needs no SDK. With it installed, a full credit-risk run
narrates live end to end, correct tiering (Haiku for routine steps, Sonnet for
the model-performance and promotion steps), each sentence grounded in the real
computed facts. A whole run costs about $0.003.

Sandip asked to raise the cap to $50 and enable live on the public link. Before
doing that I changed what the cap means. It was enforced per gateway instance,
and the orchestrator builds a fresh gateway per run, so it was really a per-run
budget, not a ceiling. A public link with a per-run budget is not capped at all.
Now the spend is process-global and cumulative: once total live spend across
every run and session hits $50, everyone falls back to scripted until the process
restarts. On a single instance that is the whole app.

Enabling it in prod meant a secret in prod. I kept the key out of git: a NoEcho
CloudFormation parameter carries it, deploy.sh reads it from the gitignored .env
at deploy time and passes it through, and it is never printed. The default stays
scripted and free; a visitor who picks Live LLM gets real narration behind the
cap.

Verified on the live site, not just locally. Fresh session, scripted still the
default, picked Live LLM, ran it. All three pre-gate steps came back marked LIVE
with real model text, and the gateway ledger showed 3 calls, 1 elevated-stakes,
$0.001772 of real spend on the instance. So the instance reaches Anthropic, the
key is wired, and the cost tracking is honest.

One naming wart: the env var is still LIVE_MODE_MONTHLY_CAP, but it is now a
cumulative-per-process ceiling that resets on restart, not a calendar month. I
left the name to avoid churn and documented the behavior in the code.

127 tests pass, ruff clean. Deployed SHA 55edb37. Live at https://sentinel.sandip.dev.
