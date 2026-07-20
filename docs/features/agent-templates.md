# Agent Templates

A screen under Governance where a template is a document you can edit, a
document that can be refused, and a document you can deploy. Before this, the
five templates were a read-only list on the Platform screen: five names, five
purposes, five tool lists, and no way to tell whether any of it was true.

## The question this answers

An editable template that has no consequence is decoration, and this build's
whole argument is that nothing here is decorative. So the design had to answer
two things: what does editing mean when the thing being edited is policy, and
what does "deploy" mean in a product that has no deployment.

The answers are the two ideas the screen is built on.

**Editing means being checked.** Every field in a template names a value that
some other module owns. A purpose is a column in the purpose matrix. An import
is a name on the codegen allow-list. A tool is declared in `agents.yaml`. A tier
is a rung on the ladder in `tiers.py`. A column is inside a grant in
`access.py`. So the editor does not need its own opinion about what is legal: it
reads the enforcing modules, and refuses anything they would refuse. Eleven
checks run on every keystroke-to-blur, reported in the Gate stage's own
language.

**Deploy means registering a draft.** Not a toast. `certification.register()`,
with the dataset's content SHA computed at that moment and pinned into the
contract, producing a real `RegistryEntry` that appears on the Registry screen
under Analysis-agents and is judged by the four certification gates. That is
what `sentinel new-agent` already does from the CLI, so the two paths to an
agent now agree. The simulated part is named on the screen: nothing is written
to disk, no process starts.

## The format: YAML

Not on general merit. On three specifics.

1. The config layer is already YAML: `rbac.yaml`, `evals.yaml`, `personas.yaml`,
   `questions.yaml`, `agents.yaml`. A sixth is consistency; a JSON one is
   divergence.
2. `scaffold.py::_spec_yaml` already writes an agent spec in YAML. The CLI and
   the screen should emit one artifact, not two formats to keep in sync. This is
   the argument that actually decided it.
3. A governance spec's *why* matters as much as its values, and JSON cannot
   carry a comment.

Serialization uses `json.dumps` for every scalar and flat list. JSON is a subset
of YAML that PyYAML reads back identically, which sidesteps every quoting
question a hand-rolled emitter would otherwise have to answer: a name with a
colon, a version that looks like a float, a null. Prose uses a `>-` folded
block, and `test_yaml_round_trip_loses_nothing` asserts the fold survives.

Rejected: a Python dataclass (editing means executing arbitrary code, which is
dead on arrival for a governance product), JSON (above), TOML (awkward for
nested lists), markdown with frontmatter (right for playbooks, wrong for closed
vocabularies), and a form with no text format (loses the property that a spec is
a file you can diff and PR, which is the whole reuse argument).

## Two kinds of check, and why they are kept apart

The distinction is the design, not a detail.

**Policy checks** are the fence: schema, pattern, tools, imports, contract,
purposes, tier, columns. A refusal disables the deploy. An illegal blueprint
should not reach the registry at all.

**Certification gates** are not the fence: evals, owner, signoff. They block
`certified`. They do not block the draft.

Every shipped template fails two certification gates, because all five ship with
`owner: UNASSIGNED` and no validator. That is deliberate: a blueprint cannot own
the instances made from it, and `scaffold.py` registers a new agent unowned for
exactly the same reason. If those refusals blocked the deploy, the CLI and this
screen would disagree about what a new agent looks like on day one.

A screen that painted "not yet owned" the same red as "reaches for the network"
would not be telling a reviewer which one is a policy violation.

## The eleven checks

| check | control | source of truth |
|---|---|---|
| document schema | — | the v1 schema; `status` and `governance` are refused as authored keys |
| architecture pattern | — | `platform/patterns.py` |
| tool allow-list | guardrails | `config/agents.yaml` |
| import allow-list | CTL-CODE-01 | `codegen/allowlist.py`, per declared tier |
| data contract | CTL-CONTRACT-01 | `datasets/registry.py` |
| purpose limitation | CTL-PURP-01 | `govflow/purpose_matrix.py` |
| autonomy ceiling | CTL-TIER-01 | `govflow/tiers.py` |
| column grant | CTL-COL-01 | `govflow/access.py` |
| eval suite | CTL-EVAL-01 | certification gate 1 |
| owner | — | certification gate 2 |
| segregation of duties | CTL-SOD-01 | certification gate 4 |

`CheckReading` and `Observation` are imported from `codegen/gate.py` rather than
redefined. Same four verdicts, same evidence chips, same computed summaries, so
a reviewer who has read the Gate panel can read this one and the two cannot
drift apart in wording.

The fourth verdict earns its keep here. `fair_lending` is the only purpose with
a defined column grant in this build, so on any other purpose the column check
is **not armed**, in amber, saying its rule was never supplied. Switching a
template's purpose from `fair_lending` to `marketing` in the editor flips that
cell from green to amber live. Painting it green would claim an assurance nobody
established.

Three checks resolve through the dataset, so a template with no contract leaves
purpose, tier and column all unable to read. The two AVAILABLE templates are in
exactly that state, which is also why they are not live.

## Things a template may not do

- **Pin a content SHA.** A SHA is a fact about one snapshot of a file. A
  blueprint pinning one would claim every instance runs against today's data.
  Deploy computes it instead.
- **Declare imports below L2.** Those tiers write no code, so an import list
  there is a contradiction in the document rather than a long list to check.
- **Assert a status.** `certification.py` computes status from the gates every
  time it is asked and never stores one. A document carrying one would assert a
  verdict nobody reached.
- **Lower the eval floor** below the certification floor, or **raise a tier
  ceiling** above the data's classification ceiling. A template may lower a
  ceiling, never raise one.
- **Name a team as owner.** A queue cannot be asked why it signed, which is the
  point of gate 2.

## Persistence

Shipped templates are never mutated. Edits live in `st.session_state` against a
per-template buffer; Revert restores from the Python objects; Download gives you
the artifact to commit. This keeps the coverage metric and the five blueprints
exactly what the tests assert, and it is honest about prod: the Elastic
Beanstalk filesystem is ephemeral, so writing edits to disk there would lose
them on the next deploy without saying so.

## Nav, and a count that had gone stale

`Governance` now reads Datasets, Agent Templates, Registry, which is lifecycle
order: the data you may use, the blueprint you build from, the inventory of what
got built. The Platform screen keeps the reuse metric and links across, rather
than printing the catalogue a second time.

Adding the tenth screen exposed an existing defect. `manual.py` opened its
screens chapter with a hand-typed "Nine screens in the sidebar", and nothing
failed when that became false. The nav definition moved out of `app.py` into
`sentinel/ui/nav.py`, both files read it, and the count is computed.
`test_the_manual_reads_its_screen_count_rather_than_stating_one` fails if a
number is typed back in. `product_screens()` excludes the Help group on purpose:
the manual, the FAQ and Ask me are the manual describing itself.

## Files

- `sentinel/platform/template_spec.py` — schema, YAML round trip, the eleven
  checks, deploy
- `sentinel/platform/templates.py` — the catalog, extended with the governance
  fields that make a template deployable
- `sentinel/ui/agent_templates.py` — the list and the editor
- `sentinel/ui/nav.py` — the sidebar definition, extracted so the manual can
  count it
- `tests/test_agent_templates.py` — 48 tests
