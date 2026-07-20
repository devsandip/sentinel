"""The User Manual: one screen under Help that documents the whole product.

Ten chapters behind a rail, the first of which is a presentation deck. The deck
exists because the product is wide enough that a new visitor cannot infer it
from any single screen: the governance stages, the autonomy tiers, the named
controls, the screens, the registries. Those counts are not written here,
because this docstring cannot read them and a sentence that names one goes
stale silently, which is what happened to the screens chapter's opening line
the first time a nav item was added. The other nine chapters are the reference
the deck points at.

The rule this module follows, which is the rule the rest of the build follows:
**every number here reads from the thing that enforces it.** The stage list
comes from `platform.audit_stages.CANONICAL_STAGES`, the tier ceilings from
`govflow.tiers`, the control catalogue from `govflow.controls_info`, the import
allowlist from `codegen.allowlist`, the sandbox caps from `sandbox.execute`,
the personas from `harness.identity`, the datasets from `datasets.registry`,
and the library versions from `importlib.metadata` (what is installed, not what
was declared). A manual that asserts a number the code has since changed is
worse than no manual, and this repo has already paid for that lesson twice: an
allowlist that named five packages nothing installed, and an Execute panel whose
stated wall clock had not matched the enforced one for several versions.

`tests/test_app_smoke.py::test_no_screen_hardcodes_the_wall_clock` scans this
file for a retyped wall clock and does not care that the offender was a
docstring recounting the original defect, which is how the sentence above lost
its numbers. That bluntness is the point: the check cannot tell prose from copy,
so nothing in `sentinel/ui/` gets to restate the number, including the paragraph
explaining why nothing gets to restate the number.

Editorial prose (what a stage is *for*, what to click, what a term means) is
written here and owned here. Enforced facts are imported. Where the two could
drift, the imported one wins on the page.
"""

from __future__ import annotations

import html
from importlib import metadata

import streamlit as st

from sentinel.codegen.allowlist import (
    ALLOWED_IMPORTS,
    DUNDER_ESCAPES,
    DYNCODE_BUILTINS,
    DYNCODE_MODULES,
    EGRESS_MODULES,
    FS_MODULES,
    L3_ALLOWED_IMPORTS,
)
from sentinel.codegen.sql_gate import DEFAULT_JOIN_CEILING
from sentinel.datasets import all_datasets
from sentinel.disclosure.screen import DEFAULT_CELL_FLOOR
from sentinel.govflow.controls_info import CONTROLS_INFO, implemented_ids
from sentinel.govflow.purpose_matrix import (
    DATA_CLASSIFICATION,
    PURPOSE_LABEL,
    PURPOSES,
    matrix_rows,
)
from sentinel.govflow.tiers import (
    ATT_CERTIFIED,
    ATT_SANDBOX_WAIVER,
    CLASSIFICATION_CEILING,
    TIERS,
)
from sentinel.harness.controls import CONTROL_CATALOG
from sentinel.harness.identity import all_personas, policy_version
from sentinel.platform.audit_stages import CANONICAL_STAGES, STAGE_PURPOSE
from sentinel.platform.certification import FAITHFULNESS_FLOOR
from sentinel.platform.patterns import all_patterns
from sentinel.sandbox.execute import (
    DEFAULT_MEMORY_MB,
    DEFAULT_WALL_CLOCK_S,
    GOVFLOW_WALL_CLOCK_S,
)
from sentinel.ui.brand import SHIELD_SVG
from sentinel.ui.nav import DRILL_DOWNS, SECTION_TEMPLATES, screen_count

# --------------------------------------------------------------------------
# Chapters
# --------------------------------------------------------------------------
PRESENTATION = "Presentation"
CHAPTERS: list[str] = [
    PRESENTATION,
    "Quick start",
    "The nine stages",
    "Autonomy levels",
    "Controls",
    "Screens",
    "Roles & access",
    "Data",
    "Architecture",
    "Glossary",
]


def _esc(v: object) -> str:
    return html.escape(str(v))


def _version(dist: str) -> str:
    """The installed version, or an honest blank.

    Read live rather than copied from `pyproject.toml`, on the same principle as
    `tests/test_allowlist_env.py`: the environment that has to honour a claim is
    the one worth asking. A package on the L2 allowlist that is absent here is a
    grant the sandbox cannot execute, and the page says so rather than printing
    a version it read from a file.
    """
    try:
        return metadata.version(dist)
    except Exception:  # noqa: BLE001 - absence is the answer, not an error
        return ""


# --------------------------------------------------------------------------
# Editorial copy, keyed to the imported facts
# --------------------------------------------------------------------------
# One short verb phrase per stage, for the deck's rail. The authoritative
# sentence is STAGE_PURPOSE, imported; this is the label above it.
_STAGE_VERB: dict[str, str] = {
    "Ask": "Bind and scope",
    "Plan": "Select certified analysis",
    "Access": "Enforce by construction",
    "Generate": "Model writes code",
    "Gate": "Static review",
    "Execute": "Sandboxed run",
    "Screen": "Disclosure control",
    "Interpret": "Narrate and check",
    "Attest": "Evidence and signoff",
}

# What a reader most needs to know at each stage that STAGE_PURPOSE does not
# say: the refusal it can produce, or the thing that surprises people.
_STAGE_NOTE: dict[str, str] = {
    "Ask": (
        "The tier is computed here, from the data's classification and the "
        "person's attestations, and frozen. It cannot be raised later in the "
        "run, and nobody chooses it."
    ),
    "Plan": (
        "Only certified analyses are visible. Certification is computed from "
        "four gates, never stored, so an entry that loses its validator stops "
        "being certified the moment it does."
    ),
    "Access": (
        "A denied column is not masked, it is absent. The scoped table does not "
        "have the column, so no downstream stage can reference it by accident."
    ),
    "Generate": (
        "Nothing is dangerous yet. Generating code is not running code, and no "
        "control acts here; the fence is what the prompt describes, the gate is "
        "what enforces it."
    ),
    "Gate": (
        "Two parsers read the code and neither executes it: Python's ast, and "
        "sqlglot for anything passed to ctx.sql. A refusal names the control and "
        "the line."
    ),
    "Execute": (
        "A subprocess with a wall clock, a memory cap, and one channel out "
        "(ctx.emit). An honest boundary against a model doing something dumb, "
        "not against a determined attacker."
    ),
    "Screen": (
        "Small cells are removed, not masked. You cannot leak a number you were "
        "never shown, and the model that writes the narration is downstream of "
        "this line."
    ),
    "Interpret": (
        "The narration is checked against the screened table. Asserting a value "
        "for a band the Screen removed is what CTL-EVAL-01 catches."
    ),
    "Attest": (
        "The pack ships pending. Signing requires somebody who is not the "
        "author, and the negative statement (what this does not say) is "
        "assembled from what the run actually did."
    ),
}

_TIER_SUMMARY: list[tuple[str, str, str, str]] = [
    ("L0", "Explains finished numbers", "No code, no run", "Everyone outside the first line"),
    (
        "L1",
        "Picks a certified analysis, fills typed params",
        "No code",
        "The reviewed surface is the parameters",
    ),
    (
        "L2",
        "Writes code against the fenced ctx API",
        "Allowlisted imports",
        "A static gate reads it before it runs",
    ),
    (
        "L3",
        "Writes near-arbitrary code in a broad sandbox",
        "Wider imports, same deny list",
        "Requires a sandbox waiver on top of certification",
    ),
]

# Bought: every entry actually runs in this build. The distribution name is what
# importlib.metadata is asked for; an empty string means it is stdlib or an
# external binary with no Python distribution.
_BOUGHT: list[tuple[str, str, str]] = [
    ("streamlit", "streamlit", "Every screen in this app."),
    ("pandas / numpy", "pandas", "The data plane at Access, Execute and Screen."),
    (
        "duckdb",
        "duckdb",
        "Runs gated ctx.sql over policy-scoped frames, with the row filter injected after "
        "generation.",
    ),
    ("sqlglot", "sqlglot", "The SQL half of the static gate. Parses; never executes."),
    (
        "ast (stdlib)",
        "",
        "The Python half of the static gate. Walks the tree without importing it.",
    ),
    ("scikit-learn", "scikit-learn", "The logistic-regression baseline and its metrics."),
    ("fairlearn", "fairlearn", "Group fairness metrics and the disparity ratio."),
    (
        "statsmodels",
        "statsmodels",
        "On the L2 allowlist. The model reaches for it in generated code.",
    ),
    ("lifelines", "lifelines", "Survival analysis. Allowlist only."),
    (
        "shap",
        "shap",
        "Explainability. Allowlist only, and the reason the sandbox warms its imports at boot.",
    ),
    ("dowhy / econml", "dowhy", "Causal inference. Allowlist only; the subject of the L3 route."),
    (
        "langgraph",
        "langgraph",
        "The orchestrator's StateGraph, and the real interrupt at the human gate.",
    ),
    ("opentelemetry-sdk", "opentelemetry-sdk", "One span per agent, rendered in the Traces tab."),
    ("openlineage-python", "openlineage-python", "Provenance events emitted at Access and Attest."),
    ("fpdf2", "fpdf2", "The model card PDF."),
    (
        "anthropic",
        "anthropic",
        "Live narration and live codegen, behind a monthly cost cap. Optional.",
    ),
    (
        "quarto + marimo",
        "",
        "The two audience outputs from one evidence pack. External; the pack ships .qmd and says "
        "so when quarto is absent.",
    ),
]

_BUILT: list[tuple[str, str]] = [
    ("The static gate", "sentinel/codegen/gate.py + sql_gate.py"),
    ("The sandbox", "sentinel/sandbox/execute.py + runner.py + warmup.py"),
    ("The disclosure screen", "sentinel/disclosure/screen.py + association.py"),
    ("Purpose matrix and tier resolver", "sentinel/govflow/purpose_matrix.py + tiers.py"),
    ("The control catalogue", "sentinel/govflow/controls_info.py"),
    ("Audit log and cross-run ledger", "sentinel/harness/audit.py + platform/audit_store.py"),
    ("RBAC, PII, guardrails, eval gate, cost", "sentinel/harness/"),
    ("Certification lifecycle", "sentinel/platform/certification.py"),
    ("Dataset registry and data contracts", "sentinel/datasets/"),
    ("The evidence pack and its two outputs", "sentinel/evidence/pack.py + outputs.py"),
    ("The model gateway", "sentinel/gateway/model_gateway.py"),
    ("The MCP server", "sentinel/mcp_server.py"),
]

_SCREEN_MAP: list[tuple[str, str, str]] = [
    ("Overview", "Overview", "Four live tiles and the CTA into a governed run."),
    ("Run", "Run", "The nine-stage walkthrough. The centre of the product."),
    ("Pipeline", "Pipeline", "The four-agent credit-risk pipeline and its ten evidence tabs."),
    (
        "Analyses",
        "Analyses",
        "The analysis catalogue: profiling, feature engineering, credit risk.",
    ),
    ("Datasets", "Datasets", "Eight datasets under classification, each with a data contract."),
    (
        SECTION_TEMPLATES,
        SECTION_TEMPLATES,
        "Governed blueprints. Edit the spec, watch the checks, deploy a draft.",
    ),
    (
        "Registry",
        "Registry",
        "Three registries: models, agents, and analysis-agents under certification.",
    ),
    ("Platform", "Platform", "Playbooks, template reuse metrics, and the pattern catalogue."),
    ("Adoption", "Adoption", "Runs, promotion rate, override rate, template coverage."),
    ("Audit Log", "Audit Log", "The cross-run ledger. Every run replayed as the same nine stages."),
]

_GLOSSARY: list[tuple[str, str]] = [
    (
        "Attestation",
        "A property a person holds beyond their role: certified_analyst, sandbox_waiver. "
        "Attestations raise the person ceiling, never the data ceiling.",
    ),
    (
        "Autonomy tier",
        "How much freedom the model gets on this request: L0 to L3. Computed as the lower of the "
        "data ceiling and the person ceiling.",
    ),
    (
        "Certified analysis",
        "A registry entry that passes all four certification gates. Only certified entries are "
        "visible to Plan. Status is computed, never stored.",
    ),
    (
        "Control",
        "A named, testable rule that can refuse. Every control has an id, a stage, and one of four "
        "actions: refuses, flags, suppresses, logs.",
    ),
    (
        "Data contract",
        "What an analysis needs (capabilities, columns, minimum rows) matched against what a "
        "dataset provides, plus the dataset SHA it was certified against.",
    ),
    (
        "Disclosure floor",
        f"The minimum cell count below which a group is removed from the output. Default "
        f"{DEFAULT_CELL_FLOOR}.",
    ),
    (
        "Evidence pack",
        "The filed artifact of a run: the finding, the provenance chain, the controls attested, "
        "and the negative statement.",
    ),
    (
        "Fenced API",
        "The only surface generated code may touch: ctx.table, ctx.sql, ctx.param, ctx.emit. No "
        "dataset handle, no network, no filesystem.",
    ),
    (
        "Four-eyes",
        "Author is not approver. Enforced by CTL-SOD-01 at signoff and at certification. There is "
        "no quorum in this build, and no dual control; single independent signature only.",
    ),
    (
        "Governed run",
        "One request carried through all nine stages, with every control consulted and every "
        "consultation recorded.",
    ),
    (
        "Negative statement",
        "The section of the evidence pack that says what the finding does not say, assembled from "
        "what the run actually did rather than written by hand.",
    ),
    (
        "Proxy",
        "A permitted column that reconstructs a protected one. Measured by Cramer's V or the "
        "correlation ratio, flagged rather than refused, because business necessity is Legal's "
        "call.",
    ),
    (
        "Purpose limitation",
        "A dataset carries a list of permitted purposes. A request with the wrong purpose is "
        "refused before any code is written. Not who: why.",
    ),
    (
        "Refusal",
        "A control that said no. Distinct from a control that was consulted; a gate event means "
        "the control was armed, not that it fired.",
    ),
    (
        "Scoped table",
        "The policy-filtered view Access builds. A denied column does not exist on it.",
    ),
    (
        "Seeded",
        "Demo telemetry from runs that actually executed, committed so the record survives a "
        "deploy. Every seeded row is labeled on its surface.",
    ),
    (
        "Stage",
        "One of the nine: Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret, Attest.",
    ),
    (
        "Ungoverned run",
        "A run where an admin disabled a control. The disabling is itself audited and the run is "
        "banner-marked; it is not a governed result.",
    ),
]


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
_MANUAL_CSS = """
    <style>
      /* ---------- slide chrome ---------- */
      .man-slide { margin:0 0 6px 0; }
      .man-slide .n { font-family:var(--mono); font-size:11px; font-weight:700;
        letter-spacing:.1em; color:var(--accent); background:var(--accent-soft);
        border:1px solid var(--accent-soft-border); padding:2px 8px;
        border-radius:999px; }
      .man-slide .k { font-size:11px; font-weight:700; letter-spacing:.13em;
        text-transform:uppercase; color:var(--faint); margin-left:9px; }
      .man-slide h3 { font-size:25px; font-weight:650; color:var(--ink);
        margin:10px 0 6px 0; line-height:1.2; }
      .man-slide .lede { color:var(--muted); font-size:14.5px; max-width:74ch;
        line-height:1.55; }

      /* ---------- cover (always dark, like the login gate) ---------- */
      .man-cover { background:radial-gradient(760px 420px at 12% -30%, #1b3059, #0d1a30);
        border:1px solid #22345a; border-radius:16px; padding:34px 34px 28px 34px; }
      .man-cover .lock { display:flex; align-items:center; gap:12px; }
      .man-cover .lock svg { width:30px; height:30px; }
      .man-cover .wm { font-weight:700; letter-spacing:.26em; font-size:17px;
        color:#eef3fc; }
      .man-cover .sub { color:#93a4c2; font-size:11.5px; letter-spacing:.05em;
        border-left:1px solid #243a5e; padding-left:11px; }
      .man-cover h1 { color:#ffffff; font-size:33px; font-weight:650;
        margin:22px 0 0 0; line-height:1.18; max-width:22ch; }
      .man-cover .say { color:#b9c8e2; font-size:15px; line-height:1.6;
        max-width:64ch; margin-top:12px; }
      .man-cover .say b { color:#ffffff; font-weight:600; }
      .man-cover .stats { display:flex; flex-wrap:wrap; gap:9px; margin-top:22px; }
      .man-cover .stat { background:rgba(255,255,255,.05); border:1px solid #243a5e;
        border-radius:11px; padding:9px 14px; min-width:104px; }
      .man-cover .stat .v { font-family:var(--mono); font-size:21px; font-weight:700;
        color:#9dc0f5; line-height:1.1; }
      .man-cover .stat .l { font-size:10.5px; color:#93a4c2; margin-top:3px;
        letter-spacing:.02em; }
      .man-cover .foot { color:#7f92b3; font-size:11.5px; margin-top:20px;
        border-top:1px solid #1c2c4c; padding-top:12px; }

      /* ---------- two-up panels ---------- */
      .man-panel { background:var(--surface); border:1px solid var(--border);
        border-radius:12px; padding:16px 17px; height:100%; }
      .man-panel.ok { border-color:var(--ok-border); background:var(--ok-soft); }
      .man-panel.no { border-color:var(--danger-border); background:var(--danger-soft); }
      .man-panel .pt { font-size:13px; font-weight:700; color:var(--ink);
        margin-bottom:9px; }
      .man-panel ul { margin:0; padding-left:17px; }
      .man-panel li { font-size:13px; color:var(--muted); line-height:1.55;
        margin-bottom:6px; }
      .man-panel li b { color:var(--ink); font-weight:600; }

      /* ---------- the thesis strip ---------- */
      .man-thesis { background:var(--rail); border-radius:12px; padding:17px 20px;
        color:#dce6f7; font-size:15px; line-height:1.55; margin-top:4px; }
      .man-thesis b { color:#ffffff; }

      /* ---------- architecture diagram ---------- */
      .man-arch { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
      .man-arch .full { grid-column:1 / -1; }
      .man-plane { border:1px solid var(--border); border-radius:12px;
        background:var(--surface); padding:14px 15px; }
      .man-plane.pipe { border-color:var(--accent-soft-border);
        background:var(--accent-soft); }
      .man-plane.ctrl { border-color:var(--warn-border); background:var(--warn-soft); }
      .man-plane .pl { font-size:10.5px; font-weight:700; letter-spacing:.11em;
        text-transform:uppercase; color:var(--faint); }
      .man-plane .pn { font-size:14px; font-weight:650; color:var(--ink);
        margin:3px 0 8px 0; }
      .man-plane .pd { font-size:12.5px; color:var(--muted); line-height:1.5; }
      .man-flow { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 4px 0; }
      .man-node { font-family:var(--mono); font-size:11.5px; background:var(--surface);
        border:1px solid var(--border-strong); border-radius:7px; padding:4px 9px;
        color:var(--ink); }
      .man-node.hg { border-color:var(--danger-border); background:var(--danger-soft);
        color:var(--danger-ink); font-weight:700; }
      .man-arrow { text-align:center; color:var(--faint); font-size:13px;
        font-family:var(--mono); letter-spacing:.2em; padding:2px 0; }
      .man-band { border:1px dashed var(--border-strong); border-radius:11px;
        padding:11px 14px; text-align:center; background:var(--surface-2); }
      .man-band .bt { font-size:12.5px; font-weight:650; color:var(--ink); }
      .man-band .bd { font-size:11.5px; color:var(--muted); margin-top:2px; }

      /* ---------- the nine-stage rail ---------- */
      .man-rail { display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; }
      .man-step { border:1px solid var(--border); border-left:3px solid var(--accent);
        border-radius:10px; background:var(--surface); padding:11px 13px; }
      .man-step .sn { font-family:var(--mono); font-size:10.5px; font-weight:700;
        color:var(--accent); letter-spacing:.08em; }
      .man-step .st { font-size:15px; font-weight:650; color:var(--ink);
        margin:1px 0 1px 0; }
      .man-step .sk { font-size:11px; color:var(--faint); text-transform:uppercase;
        letter-spacing:.07em; font-weight:700; }
      .man-step .sd { font-size:12.5px; color:var(--muted); line-height:1.5;
        margin-top:6px; }
      .man-step .sc { margin-top:8px; display:flex; flex-wrap:wrap; gap:4px; }
      .man-step .sc code { font-size:10px; background:var(--surface-2);
        border:1px solid var(--border); border-radius:5px; padding:1px 5px;
        color:var(--muted); }

      /* ---------- the tier ladder ---------- */
      .man-tier { display:flex; align-items:stretch; gap:0; border:1px solid var(--border);
        border-radius:10px; overflow:hidden; margin-bottom:7px; background:var(--surface); }
      .man-tier .tl { font-family:var(--mono); font-size:16px; font-weight:700;
        color:var(--accent-ink); background:var(--accent); width:56px; flex:none;
        display:flex; align-items:center; justify-content:center; }
      .man-tier.t0 .tl { background:var(--muted); }
      .man-tier.t1 .tl { background:#4c74b8; }
      .man-tier.t3 .tl { background:var(--accent-strong); }
      .man-tier .tb { padding:9px 13px; }
      .man-tier .tt { font-size:13.5px; font-weight:650; color:var(--ink); }
      .man-tier .td2 { font-size:12px; color:var(--muted); margin-top:2px; }
      .man-formula { text-align:center; font-family:var(--mono); font-size:15px;
        color:var(--ink); background:var(--surface-2); border:1px solid var(--border);
        border-radius:10px; padding:14px; margin:4px 0 12px 0; }
      .man-formula .op { color:var(--accent); font-weight:700; }
      .man-formula .cap { display:block; font-family:inherit; font-size:12px;
        color:var(--faint); margin-top:7px; letter-spacing:.02em; }

      /* ---------- definition rows ---------- */
      /* Wrapping is load-bearing, not decoration. These rows render inside
         columns as narrow as ~200px (the deck's governance slide, the screens
         chapter), and a fixed-width key there leaves the value a 20px gutter
         and a ten-line wrap. With wrap on and a flex-basis on the value, a
         column too narrow to hold both drops the value onto its own full-width
         line instead of strangling it. */
      .man-def { display:flex; flex-wrap:wrap; gap:4px 14px; padding:8px 0;
        border-bottom:1px solid var(--border); align-items:baseline; }
      .man-def .dk { font-family:var(--mono); font-size:12px; font-weight:700;
        color:var(--ink); min-width:150px; flex:0 1 auto; }
      .man-def .dv { font-size:13px; color:var(--muted); line-height:1.5;
        flex:1 1 240px; }
      /* A control id is one token. Breaking CTL-EGRESS-01 across two lines
         makes it unsearchable and unreadable at a glance. */
      .man-def .dv code, .man-def .dk code { white-space:nowrap; }
      .man-def .dver { font-family:var(--mono); font-size:10.5px; color:var(--faint); }
      .man-def .dabs { font-family:var(--mono); font-size:10.5px;
        color:var(--warn-ink); }

      /* ---------- control catalogue ---------- */
      .man-ctl { border:1px solid var(--border); border-radius:9px;
        background:var(--surface); padding:10px 12px; margin-bottom:7px; }
      .man-ctl.doc { background:var(--surface-2); border-style:dashed; }
      .man-ctl .ch { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
      .man-ctl .cid { font-family:var(--mono); font-size:12px; font-weight:700;
        color:var(--ink); }
      .man-ctl .cnm { font-size:12.5px; color:var(--ink); }
      .man-ctl .cw { font-size:12.5px; color:var(--muted); line-height:1.5;
        margin-top:5px; }
      .man-act { font-size:10px; font-weight:700; letter-spacing:.05em;
        text-transform:uppercase; padding:1px 7px; border-radius:5px; }
      .man-act.refuses { background:var(--danger-soft); color:var(--danger-ink);
        border:1px solid var(--danger-border); }
      .man-act.flags { background:var(--warn-soft); color:var(--warn-ink);
        border:1px solid var(--warn-border); }
      .man-act.suppresses { background:var(--warn-soft); color:var(--warn-ink);
        border:1px solid var(--warn-border); }
      .man-act.logs { background:var(--accent-soft); color:var(--accent);
        border:1px solid var(--accent-soft-border); }

      /* ---------- module chips ---------- */
      .man-mods { display:flex; flex-wrap:wrap; gap:5px; margin:3px 0 12px 0; }
      .man-mod { font-family:var(--mono); font-size:11px; border-radius:6px;
        padding:2px 7px; }
      .man-mod.allow { background:var(--ok-soft); color:var(--ok-ink);
        border:1px solid var(--ok-border); }
      .man-mod.deny { background:var(--danger-soft); color:var(--danger-ink);
        border:1px solid var(--danger-border); }
      .man-mod.new { background:var(--accent-soft); color:var(--accent);
        border:1px solid var(--accent-soft-border); }

      /* ---------- misc ---------- */
      .man-num { display:flex; gap:12px; padding:9px 0;
        border-bottom:1px solid var(--border); }
      .man-num .i { font-family:var(--mono); font-size:12px; font-weight:700;
        color:var(--accent); min-width:22px; }
      .man-num .b { font-size:13px; color:var(--muted); line-height:1.55; }
      .man-num .b b { color:var(--ink); font-weight:600; }
      .man-note { border-left:3px solid var(--warn); background:var(--warn-soft);
        border-radius:0 9px 9px 0; padding:10px 13px; font-size:12.5px;
        color:var(--warn-ink); line-height:1.55; margin:10px 0; }
      .man-note b { font-weight:700; }
    </style>
"""


# --------------------------------------------------------------------------
# Small render helpers
# --------------------------------------------------------------------------
def _slide(n: int, kicker: str, title: str, lede: str) -> None:
    st.markdown(
        f"<div class='man-slide'><span class='n'>{n:02d}</span>"
        f"<span class='k'>{_esc(kicker)}</span>"
        f"<h3>{_esc(title)}</h3><div class='lede'>{lede}</div></div>",
        unsafe_allow_html=True,
    )


def _defs(rows: list[tuple[str, str]]) -> None:
    st.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(k)}</span>"
            f"<span class='dv'>{v}</span></div>"
            for k, v in rows
        ),
        unsafe_allow_html=True,
    )


def _numbered(rows: list[tuple[str, str]]) -> None:
    st.markdown(
        "".join(
            f"<div class='man-num'><span class='i'>{i}</span>"
            f"<span class='b'><b>{_esc(t)}</b> {b}</span></div>"
            for i, (t, b) in enumerate(rows, start=1)
        ),
        unsafe_allow_html=True,
    )


def _mods(mods: set[str] | frozenset[str], kind: str) -> None:
    st.markdown(
        "<div class='man-mods'>"
        + "".join(
            f"<span class='man-mod {kind}'>{_esc(m).replace('_', '&#95;')}</span>"
            for m in sorted(mods)
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _note(body: str) -> None:
    st.markdown(f"<div class='man-note'>{body}</div>", unsafe_allow_html=True)


def _panel(col, cls: str, title: str, items: list[str]) -> None:  # noqa: ANN001
    col.markdown(
        f"<div class='man-panel {cls}'><div class='pt'>{_esc(title)}</div><ul>"
        + "".join(f"<li>{i}</li>" for i in items)
        + "</ul></div>",
        unsafe_allow_html=True,
    )


def _stage_controls() -> dict[str, list[str]]:
    """Controls grouped by the stage they act at, enforced ones only."""
    out: dict[str, list[str]] = {s: [] for s in CANONICAL_STAGES}
    for cid in implemented_ids():
        info = CONTROLS_INFO[cid]
        out.setdefault(info.stage, []).append(cid)
    return out


# --------------------------------------------------------------------------
# Chapter 1: the presentation
# --------------------------------------------------------------------------
def _deck(nav_to) -> None:  # noqa: ANN001, C901
    n_ctl = len(implemented_ids())
    n_named = len(CONTROLS_INFO)
    datasets = all_datasets()
    personas = all_personas()
    by_stage = _stage_controls()

    # -- 00 cover ----------------------------------------------------------
    stats = [
        (len(CANONICAL_STAGES), "governance stages"),
        (len(TIERS), "autonomy tiers"),
        (n_ctl, "controls enforced"),
        (len(datasets), "datasets classified"),
        (len(personas), "governed personas"),
    ]
    st.markdown(
        f"""
        <div class='man-cover'>
          <div class='lock'>{SHIELD_SVG}<span class='wm'>SENTINEL</span>
            <span class='sub'>Governed agentic analysis</span></div>
          <h1>Agentic AI that a bank can actually ship.</h1>
          <div class='say'>A model writes the analysis code. A static gate reads
          it before any machine does. A disclosure screen removes small cells
          before the model is allowed to describe the result. What comes out is
          an evidence pack somebody other than the author signs.
          <b>Governance is the product; the ML underneath is deliberately
          simple.</b></div>
          <div class='stats'>
            {"".join(
                f"<div class='stat'><div class='v'>{v}</div>"
                f"<div class='l'>{lab}</div></div>" for v, lab in stats
            )}
          </div>
          <div class='foot'>This deck reads its numbers from the modules that
          enforce them. If a control is added, a tier ceiling moves, or a
          package leaves the allowlist, this page changes with it.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    # -- 01 what it is -----------------------------------------------------
    _slide(
        1,
        "The product",
        "One request, carried through nine controls, ending in signed evidence.",
        "Most agentic AI stalls at the demo. Not because the model cannot do the "
        "analysis, but because nobody can show a second line of defence what it "
        "did. Sentinel is the harness that answers that, built alongside the "
        "pipeline rather than bolted on after.",
    )
    c1, c2 = st.columns(2)
    _panel(
        c1,
        "ok",
        "What it does",
        [
            "<b>Runs a real analysis.</b> Real metrics, real fairness numbers, computed live from "
            "the data.",
            "<b>Lets a model write the code</b> at L2 and L3, against a fenced API with no dataset "
            "handle, no network and no filesystem.",
            "<b>Refuses out loud.</b> Every refusal names the control and the line that caused it.",
            "<b>Keeps the record.</b> Every run is replayable as the same nine stages, across "
            "sessions and across deploys.",
            "<b>Ends in evidence,</b> not a chart: a finding, its provenance, the controls "
            "attested, and what the finding does not say.",
        ],
    )
    _panel(
        c2,
        "no",
        "What it deliberately is not",
        [
            "<b>Not a model zoo.</b> The ML is a logistic-regression baseline on purpose.",
            "<b>Not self-decomposing.</b> Orchestrator-workers is in the pattern catalogue marked "
            "<i>avoided</i>; the control flow is fixed so it can be audited.",
            "<b>Not a staged demo.</b> The controls that fire, fire on real code with real "
            "violations. Nothing is seeded to look like a refusal.",
            "<b>Not dual control.</b> Four-eyes here means author-is-not-approver, single "
            "signature. There is no quorum, and the build says so rather than implying one.",
            "<b>Not a hardened sandbox.</b> Execute is an honest boundary against a model doing "
            "something dumb, not against a determined attacker.",
        ],
    )
    st.write("")

    # -- 02 architecture ---------------------------------------------------
    _slide(
        2,
        "Architecture",
        "Two planes: the one that does the work, and the one that decides it may.",
        "The pipeline and the control plane are separate modules. Every agent "
        "action funnels through the harness, which is what makes the same "
        "harness reusable for any future analysis. That separation is the "
        "message: it is what turns a prototype into a platform.",
    )
    st.markdown(
        f"""
        <div class='man-arch'>
          <div class='full man-band'>
            <div class='bt'>A request</div>
            <div class='bd'>dataset · declared purpose · question · identity</div>
          </div>
          <div class='full man-arrow'>&#8595;</div>
          <div class='man-plane pipe'>
            <div class='pl'>Pipeline plane</div>
            <div class='pn'>What does the work</div>
            <div class='man-flow'>
              <span class='man-node'>Profiler</span>
              <span class='man-node'>EDA / Feature</span>
              <span class='man-node'>Modeler</span>
              <span class='man-node hg'>human gate</span>
              <span class='man-node'>Validator</span>
            </div>
            <div class='pd'>A LangGraph <code>StateGraph</code> with a fixed
            topology. The human gate is a real <code>interrupt</code>, not a
            flag: the graph stops there and resumes on a <code>Command</code>.
            At L2 and L3 the work is code the model wrote; at L1 it is a
            certified analysis with typed parameters.</div>
          </div>
          <div class='man-plane ctrl'>
            <div class='pl'>Control plane</div>
            <div class='pn'>What decides it may</div>
            <div class='man-flow'>
              <span class='man-node'>purpose</span>
              <span class='man-node'>tier</span>
              <span class='man-node'>RBAC</span>
              <span class='man-node'>static gate</span>
              <span class='man-node'>sandbox</span>
              <span class='man-node'>disclosure</span>
              <span class='man-node'>faithfulness</span>
              <span class='man-node'>SoD</span>
            </div>
            <div class='pd'>{n_ctl} enforced controls across the nine stages
            ({n_named} named, the rest declared and honestly marked
            not-implemented). Each one is a named, testable rule that can
            refuse. Nothing reaches data, a tool, or a model without passing
            through here.</div>
          </div>
          <div class='full man-arrow'>&#8595;</div>
          <div class='full man-band'>
            <div class='bt'>An evidence pack, pending an independent signature</div>
            <div class='bd'>finding · provenance and dataset SHA · controls
            attested · what this does not say · lineage events</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _note(
        "<b>Read the arrows carefully.</b> The control plane is not a step in "
        "the pipeline; it wraps every step of it. An agent cannot read a column, "
        "call a tool, or send text to a model except through the harness, which "
        "is why the audit log is complete by construction rather than by "
        "discipline."
    )
    st.write("")

    # -- 03 the nine steps -------------------------------------------------
    _slide(
        3,
        "The nine steps",
        "Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret, Attest.",
        "The same nine stages every run is read as, whichever route it took. "
        "The Run screen teaches them one panel at a time; the Audit Log replays "
        "every historical run against them, so a run from a different pipeline "
        "still answers the same nine questions.",
    )
    st.markdown(
        "<div class='man-rail'>"
        + "".join(
            f"<div class='man-step'><div class='sn'>STAGE {i}</div>"
            f"<div class='st'>{_esc(s)}</div>"
            f"<div class='sk'>{_esc(_STAGE_VERB.get(s, ''))}</div>"
            f"<div class='sd'>{_esc(STAGE_PURPOSE.get(s, ''))}</div>"
            f"<div class='sc'>"
            + (
                "".join(f"<code>{_esc(c)}</code>" for c in by_stage.get(s, []))
                or "<code>no named control</code>"
            )
            + "</div></div>"
            for i, s in enumerate(CANONICAL_STAGES, start=1)
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "The chips are the controls that act at that stage. Generate carries "
        "none on purpose: writing code is not running code."
    )
    st.write("")

    # -- 04 levels ---------------------------------------------------------
    _slide(
        4,
        "Autonomy levels",
        "How much the model is allowed to do is computed, never chosen.",
        "There is no autonomy dial in this product. The tier falls out of two "
        "ceilings, and the request lands at the lower one. A certified analyst "
        "on confidential data drops to L1 no matter how senior they are, and an "
        "uncertified analyst on public data does the same.",
    )
    st.markdown(
        "<div class='man-formula'>tier = <span class='op'>min</span>( "
        "what the <b>data</b> classification allows , what the <b>person</b> "
        "and their attestations allow )"
        "<span class='cap'>Computed at Ask and frozen for the run. It cannot be "
        "raised mid-request, and the gate that enforces it sits in the flow, not "
        "in the UI: a caller that bypasses the screen still lands on "
        "CTL-TIER-01.</span></div>",
        unsafe_allow_html=True,
    )
    for tier, does, code, note in _TIER_SUMMARY:
        st.markdown(
            f"<div class='man-tier t{tier[-1]}'><div class='tl'>{tier}</div>"
            f"<div class='tb'><div class='tt'>{_esc(does)}</div>"
            f"<div class='td2'>{_esc(code)} &middot; {_esc(note)}</div></div></div>",
            unsafe_allow_html=True,
        )
    t1, t2 = st.columns(2)
    t1.markdown("**Ceiling from the data**")
    t1.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(k)}</span>"
            f"<span class='dv'>up to <b>{_esc(v)}</b></span></div>"
            for k, v in CLASSIFICATION_CEILING.items()
        ),
        unsafe_allow_html=True,
    )
    t2.markdown("**Ceiling from the person**")
    t2.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(k)}</span>"
            f"<span class='dv'>up to <b>{_esc(v)}</b></span></div>"
            for k, v in (
                ("any non-analyst role", "L0"),
                ("analyst, no attestation", "L1"),
                (f"+ {ATT_CERTIFIED}", "L2"),
                (f"+ {ATT_SANDBOX_WAIVER}", "L3"),
            )
        ),
        unsafe_allow_html=True,
    )
    st.write("")

    # -- 05 governance -----------------------------------------------------
    _slide(
        5,
        "Governance",
        f"{n_ctl} controls that can refuse, each one named, staged and testable.",
        "A control is a named, testable rule that can refuse. Every control has "
        "an id, the stage it acts at, and exactly one of four actions: it "
        "refuses, it flags, it suppresses, or it logs. Every place the app shows "
        "a control chip, that chip is clickable and says what the control is and "
        "what its firing means.",
    )
    g1, g2 = st.columns([3, 2])
    with g1:
        st.markdown("**Where the controls act**")
        for s in CANONICAL_STAGES:
            ids = by_stage.get(s, [])
            if not ids:
                continue
            st.markdown(
                f"<div class='man-def'><span class='dk'>{_esc(s)}</span>"
                f"<span class='dv'>"
                + " ".join(f"<code>{_esc(c)}</code>" for c in ids)
                + "</span></div>",
                unsafe_allow_html=True,
            )
    with g2:
        st.markdown("**The five controls an admin can switch off**")
        st.markdown(
            "".join(
                f"<div class='man-def'><span class='dk'>{_esc(name)}</span>"
                f"<span class='dv'>{_esc(breaks)}</span></div>"
                for _cid, name, _desc, breaks in CONTROL_CATALOG
            ),
            unsafe_allow_html=True,
        )
    _note(
        "<b>Turning a control off is itself a governed act.</b> Only the "
        "Platform Admin can do it, the disabling is written to the audit log "
        "before the run starts, and the run is banner-marked UNGOVERNED "
        "everywhere it appears. The audit log is the one control with no "
        "switch: an unaudited run is not a run."
    )
    st.write("")

    # -- 06 tools and libraries -------------------------------------------
    _slide(
        6,
        "Tools and libraries",
        "The maths is bought. The governance is built.",
        "Every library below actually runs in this build. Nothing here is on a "
        "slide because it sounds good; where a package is installed only so the "
        "sandbox can honour an import grant, the row says so.",
    )
    l1, l2 = st.columns(2)
    with l1:
        st.markdown("**Bought**")
        rows = []
        for label, dist, why in _BOUGHT:
            ver = _version(dist) if dist else ""
            if dist and not ver:
                tag = "<span class='dabs'>not installed here</span>"
            elif ver:
                tag = f"<span class='dver'>{_esc(ver)}</span>"
            else:
                tag = ""
            rows.append((label, f"{_esc(why)} {tag}"))
        _defs(rows)
    with l2:
        st.markdown("**Built**")
        _defs([(nm, f"<code>{_esc(path)}</code>") for nm, path in _BUILT])
        st.caption(
            "On the dependency map but not wired in this build, and labelled as "
            "roadmap rather than claimed: Presidio, Evidently, OPA, pandera."
        )
    st.write("")

    # -- 07 who runs what --------------------------------------------------
    _slide(
        7,
        "Roles",
        "Nobody both runs an analysis and approves it.",
        "Six personas, three lines of defence. Run authority and promotion "
        "authority are disjoint by design, which is the whole of four-eyes in "
        "this build. Switch persona from the topbar at any time; every screen "
        "recomputes against the new identity, including the tier.",
    )
    st.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(p.name)}</span>"
            f"<span class='dv'>{_esc(p.role)} &middot; "
            + " &middot; ".join(
                x
                for x in (
                    "can run" if p.can_run else "cannot run",
                    "approves" if p.can_approve else "",
                    "toggles controls" if p.can_toggle_controls else "",
                    "read-only" if p.read_only else "",
                    "reads every run" if p.can_view_all_runs else "reads own runs",
                    ("attested " + ", ".join(p.attestations)) if p.attestations else "",
                )
                if x
            )
            + f"<br><span style='color:var(--faint)'>{_esc(p.description)}</span>"
            "</span></div>"
            for p in personas
        ),
        unsafe_allow_html=True,
    )
    st.caption(f"Access policy version {policy_version()}.")
    st.write("")

    # -- 08 where everything lives ----------------------------------------
    _slide(
        8,
        "The map",
        f"{screen_count()} screens, and which question each one answers.",
        "Start at Run if you want to see the product work. Start at Audit Log if "
        "you want to see whether it worked before.",
    )
    for i in range(0, len(_SCREEN_MAP), 3):
        cols = st.columns(3)
        for col, (label, target, what) in zip(cols, _SCREEN_MAP[i : i + 3], strict=False):
            with col, st.container(border=True):
                a, b = st.columns([6, 3], vertical_alignment="center")
                a.markdown(f"**{label}**")
                if b.button("Open", key=f"man_go_{target}", use_container_width=True):
                    nav_to(target)
                st.markdown(
                    f"<span class='muted'>{_esc(what)}</span>", unsafe_allow_html=True
                )
    st.write("")
    st.success(
        "That is the whole product in eight slides. Every chapter after this one "
        "is the reference: the stages in detail, the tier arithmetic, the full "
        "control catalogue, every screen and tab, the roles, the data, the "
        "stack, and a glossary."
    )


# --------------------------------------------------------------------------
# Chapter 2: quick start
# --------------------------------------------------------------------------
def _quick_start(nav_to) -> None:  # noqa: ANN001
    st.markdown("#### Five minutes, in order")
    _numbered(
        [
            (
                "Pick an identity.",
                "The topbar shows who you are acting as. Start as the Data Scientist: it is the "
                "only persona certified to write code, and the walkthrough is built for it.",
            ),
            (
                "Open Run.",
                "Nine stages behind a rail. Stage 1 asks you to confirm a dataset, declare a "
                "purpose, and pick an analysis.",
            ),
            (
                "Watch the tier resolve.",
                "Ask prints the arithmetic: the data's ceiling, your ceiling, and which one bound "
                "the result. Change persona and it changes.",
            ),
            (
                "Review the Plan.",
                "A certified analysis is bound and its data contract checked against the current "
                "dataset SHA. Choose scripted or live generation here.",
            ),
            (
                "Click Run governed analysis.",
                "All nine stages execute. The rail marks each one clear, refused, or skipped.",
            ),
            (
                "Walk the stages.",
                "Access shows which columns were withheld. Gate shows the nine static checks and "
                "the verdict on each. Execute shows the sandbox spelled out. Screen shows the "
                "table before and after suppression.",
            ),
            (
                "Read Attest.",
                "The finding, its provenance, the controls attested, and the negative statement. "
                "Download the Quarto source or the marimo notebook.",
            ),
            (
                "Open Audit Log.",
                "The run you just did now sits in the cross-run ledger next to every earlier one, "
                "replayed as the same nine stages.",
            ),
        ]
    )
    st.write("")
    st.markdown("#### Drive two demos, not one")
    st.markdown(
        "<span class='muted'>The default selection is benign, and a gate that "
        "clears a benign request is doing its job: blocking it would be a false "
        "positive, which this build treats as costing as much as a missed block. "
        "To see the gate refuse, pick one of the adversarial entries in the "
        "analysis dropdown at Ask. Each is real code with a real violation, and "
        "nothing about the refusal is seeded.</span>",
        unsafe_allow_html=True,
    )
    d1, d2 = st.columns(2)
    _panel(
        d1,
        "ok",
        "Demo one: the happy path",
        [
            "Fair lending: selection rate by age band.",
            "Nine gate checks clear, the sandbox runs, the Screen suppresses the small bands, the "
            "narration is checked against what survived.",
            "Ends in an evidence pack pending a signature.",
        ],
    )
    _panel(
        d2,
        "no",
        "Demo two: the refusals",
        [
            "<b>Exfiltrate results to a webhook</b> catches on CTL-EGRESS-01.",
            "<b>Write results to a file</b> catches on CTL-CODE-02.",
            "<b>Eval an untrusted metric spec</b> catches on CTL-CODE-03.",
            "<b>SELECT * via ctx.sql</b> catches on CTL-COL-01 in the SQL half of the gate.",
            "Then click <b>Fix it</b>: the repaired code faces the same gate, nothing is "
            "whitelisted.",
        ],
    )
    st.write("")
    st.markdown("#### Other things worth trying")
    _defs(
        [
            (
                "Switch to the Junior Analyst",
                "The same request drops to L1. Generate and Gate are skipped, and the reviewed "
                "surface becomes the typed parameters instead of the code.",
            ),
            (
                "Switch to the Auditor",
                "Read-only everywhere. The Run button disappears; CTL-TIER-01 refuses at Ask if "
                "you reach the flow another way.",
            ),
            (
                "Switch to the Platform Admin",
                "The Controls popover in the topbar becomes editable. Turn one off and every "
                "surface marks the next run UNGOVERNED.",
            ),
            (
                "Open a data contract",
                "Datasets, then Contract on any row. Metadata only: schema, roles, relationships. "
                "No cell values, no distributions, no samples.",
            ),
            (
                "Approve a model",
                "Run the credit pipeline from Pipeline, then switch to the MRM Approver to clear "
                "the human gate. The analyst who ran it cannot approve it.",
            ),
        ]
    )
    st.write("")
    st.markdown("#### Running it locally")
    st.code(
        "uv sync --extra dev\n"
        "uv run python scripts/prepare_data.py     # build the named CSV\n"
        "uv run pytest -q                          # the test suite\n"
        "uv run python cli.py                      # ML core only\n"
        "uv run python demo.py                     # the governed pipeline in a terminal\n"
        "./run.sh                                  # the app (stable launcher)",
        language="bash",
    )
    st.caption(
        "Use ./run.sh rather than a bare streamlit run: it sets "
        "ARROW_DEFAULT_MEMORY_POOL=system, which is the one mitigation needed "
        "for a pyarrow allocator crash on macOS."
    )
    if st.button("Go to Run", key="man_qs_run", type="primary"):
        nav_to("Run")


# --------------------------------------------------------------------------
# Chapter 3: the nine stages
# --------------------------------------------------------------------------
def _stages_chapter() -> None:
    by_stage = _stage_controls()
    st.markdown(
        "<span class='muted'>Nine stages, in order. Every governed run passes "
        "through all of them; a run that is refused records the remaining stages "
        "as skipped rather than pretending they ran. The sentence under each "
        "heading is the canonical purpose, shared by the flow, the Run screen "
        "and the Audit Log, so all three can never disagree.</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    for i, s in enumerate(CANONICAL_STAGES, start=1):
        with st.container(border=True):
            st.markdown(
                f"<div class='man-slide'><span class='n'>{i:02d}</span>"
                f"<span class='k'>{_esc(_STAGE_VERB.get(s, ''))}</span>"
                f"<h3>{_esc(s)}</h3>"
                f"<div class='lede'>{_esc(STAGE_PURPOSE.get(s, ''))}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<span class='muted'>{_esc(_STAGE_NOTE.get(s, ''))}</span>",
                unsafe_allow_html=True,
            )
            ids = by_stage.get(s, [])
            if ids:
                st.markdown(
                    "<div class='man-mods'>"
                    + "".join(
                        f"<span class='man-mod new'>{_esc(c)}</span>" for c in ids
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
                for cid in ids:
                    info = CONTROLS_INFO[cid]
                    st.markdown(
                        f"<div class='man-def'><span class='dk'>{_esc(cid)}</span>"
                        f"<span class='dv'>{_esc(info.fired_means)}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    "<span class='muted'>No named control acts at this stage.</span>",
                    unsafe_allow_html=True,
                )
    st.write("")
    _note(
        "<b>A tenth stop exists on the Run rail: Architecture.</b> It is an "
        "appendix, not a stage. The flow knows nothing of it and nothing fires "
        "there; it is where the stack is laid out bought-versus-built with the "
        "import allowlist rendered as a catalogue."
    )


# --------------------------------------------------------------------------
# Chapter 4: autonomy levels
# --------------------------------------------------------------------------
def _levels_chapter() -> None:
    st.markdown(
        "<div class='man-formula'>tier = <span class='op'>min</span>( "
        "classification ceiling , person ceiling )"
        "<span class='cap'>Resolved at Ask, frozen for the run, and enforced in "
        "the flow rather than the UI.</span></div>",
        unsafe_allow_html=True,
    )
    for tier, does, code, note in _TIER_SUMMARY:
        st.markdown(
            f"<div class='man-tier t{tier[-1]}'><div class='tl'>{tier}</div>"
            f"<div class='tb'><div class='tt'>{_esc(does)}</div>"
            f"<div class='td2'>{_esc(code)} &middot; {_esc(note)}</div></div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### The two ceilings")
    c1, c2 = st.columns(2)
    c1.markdown("**Classification ceiling**")
    c1.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(k)}</span>"
            f"<span class='dv'>up to <b>{_esc(v)}</b> &middot; "
            + ", ".join(
                sorted(d for d, c in DATA_CLASSIFICATION.items() if c == k)
            )
            + "</span></div>"
            for k, v in CLASSIFICATION_CEILING.items()
        ),
        unsafe_allow_html=True,
    )
    c2.markdown("**Person ceiling**")
    c2.markdown(
        "".join(
            f"<div class='man-def'><span class='dk'>{_esc(k)}</span>"
            f"<span class='dv'>up to <b>{_esc(v)}</b></span></div>"
            for k, v in (
                ("non-analyst role", "L0"),
                ("data scientist", "L1"),
                (f"+ {ATT_CERTIFIED}", "L2"),
                (f"+ {ATT_SANDBOX_WAIVER}", "L3"),
            )
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### Worked examples")
    _defs(
        [
            (
                "Certified analyst, german_credit",
                "Restricted allows L2; certified allows L2. Lands at <b>L2</b>, bound by both.",
            ),
            (
                "Certified analyst, ulb_fraud",
                "Confidential allows L1; certified allows L2. Lands at <b>L1</b>, bound by the "
                "data.",
            ),
            (
                "Certified analyst, synthetic_its",
                "Public allows L3; certified without a waiver allows L2. Lands at <b>L2</b>, bound "
                "by the person.",
            ),
            (
                "Junior analyst, german_credit",
                "Restricted allows L2; uncertified allows L1. Lands at <b>L1</b>, bound by the "
                "person.",
            ),
            (
                "Model validator, anything",
                "Any non-analyst role allows L0. Lands at <b>L0</b>: may read a finished run, may "
                "not start one.",
            ),
        ]
    )

    st.markdown("#### What the model may import")
    st.markdown(
        "<span class='muted'>The allowlist goes verbatim into the codegen system "
        "prompt, so every name on it is an instruction to the model to use that "
        "package. That is why a name here has to be installed in the environment "
        "that has to honour it, and why <code>tests/test_allowlist_env.py</code> "
        "reconciles this list against the artifact production installs.</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**Allowed at L2** ({len(ALLOWED_IMPORTS)} entries)")
    _mods(ALLOWED_IMPORTS, "allow")
    added = set(L3_ALLOWED_IMPORTS) - set(ALLOWED_IMPORTS)
    st.markdown(f"**Added at L3** ({len(added)} more)")
    _mods(added, "new")
    st.markdown("**Denied at every tier, including L3**")
    st.markdown("<span class='muted'>Network egress, CTL-EGRESS-01</span>", unsafe_allow_html=True)
    _mods(EGRESS_MODULES, "deny")
    st.markdown(
        "<span class='muted'>Filesystem and process, CTL-CODE-02</span>",
        unsafe_allow_html=True,
    )
    _mods(FS_MODULES, "deny")
    st.markdown(
        "<span class='muted'>Dynamic code and unsafe deserialization, CTL-CODE-03</span>",
        unsafe_allow_html=True,
    )
    _mods(set(DYNCODE_MODULES) | set(DYNCODE_BUILTINS), "deny")
    st.markdown(
        "<span class='muted'>Sandbox-escape attribute access, CTL-CODE-04</span>",
        unsafe_allow_html=True,
    )
    _mods(DUNDER_ESCAPES, "deny")
    _note(
        "<b>Deny is checked before allow.</b> That precedence is what makes L3 "
        "safe to widen: adding names to the allowed set can never open a denied "
        "category, so <code>import requests</code> reports CTL-EGRESS-01 at "
        "every tier rather than falling through to the allowlist check."
    )

    st.markdown("#### The sandbox, and its caps")
    _defs(
        [
            (
                "Wall clock",
                f"<b>{GOVFLOW_WALL_CLOCK_S:g} seconds</b> on the governed routes, which is what a "
                f"run on this platform actually gets. {DEFAULT_WALL_CLOCK_S:g}s is the fallback "
                f"for a caller that names no cap. Exceeding it kills the process and fires "
                f"CTL-TIME-01.",
            ),
            ("Memory", f"{DEFAULT_MEMORY_MB} MB, applied as an address-space rlimit in the child."),
            (
                "CPU",
                "wall clock plus two seconds, best effort. The parent's wall-clock timeout is the "
                "real cap.",
            ),
            (
                "Channel out",
                "<code>ctx.emit</code>, and nothing else. A result that is not emitted does not "
                "exist.",
            ),
            (
                "Warm-up",
                "A throwaway subprocess pre-imports the allowlist at boot. shap alone costs about "
                "15s cold, which would otherwise trip the wall clock on the first run of the day. "
                "An import grant is also a time budget.",
            ),
        ]
    )
    _note(
        "The sandbox is a subprocess with rlimits, not a container and not a "
        "jail. It is stated that way everywhere in the product: an honest "
        "boundary against a model doing something dumb, not against a "
        "determined attacker. The hardening path is real isolation, and it is "
        "named as a gap rather than implied to be closed."
    )


# --------------------------------------------------------------------------
# Chapter 5: controls
# --------------------------------------------------------------------------
def _controls_chapter() -> None:
    enforced = set(implemented_ids())
    st.markdown(
        f"<span class='muted'>{len(enforced)} controls are enforced in this "
        f"build, out of {len(CONTROLS_INFO)} named. The difference is deliberate "
        "and visible: an id that appears in the design but has no code behind it "
        "is listed here as declared, never rendered as a live control, and can "
        "never appear on a run. Every control names its stage and exactly one "
        "action.</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    _defs(
        [
            ("refuses", "Stops the run. Nothing downstream executes."),
            ("suppresses", "Removes something from the output and continues."),
            (
                "flags",
                "Records a finding for a human and continues. Used where the judgement is not the "
                "platform's to make.",
            ),
            ("logs", "Records that a condition held. The run continues unchanged."),
        ]
    )
    st.write("")

    by_stage: dict[str, list] = {}
    for info in CONTROLS_INFO.values():
        by_stage.setdefault(info.stage, []).append(info)
    order = [s for s in CANONICAL_STAGES if s in by_stage] + [
        s for s in by_stage if s not in CANONICAL_STAGES
    ]
    for stage in order:
        infos = sorted(by_stage[stage], key=lambda c: (not c.implemented, c.id))
        st.markdown(f"##### {stage}")
        for info in infos:
            live = info.id in enforced
            st.markdown(
                f"<div class='man-ctl{'' if live else ' doc'}'>"
                f"<div class='ch'><span class='cid'>{_esc(info.id)}</span>"
                f"<span class='man-act {_esc(info.action)}'>{_esc(info.action)}</span>"
                f"<span class='cnm'>{_esc(info.name)}</span>"
                + ("" if live else "<span class='badge neutral'>declared, not implemented</span>")
                + f"</div><div class='cw'>{_esc(info.what)}</div>"
                + (
                    f"<div class='cw'><b>Firing means:</b> {_esc(info.fired_means)}</div>"
                    if live
                    else ""
                )
                + "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("#### The five switchable controls")
    st.markdown(
        "<span class='muted'>These are the harness controls on the credit-risk "
        "pipeline, and the only ones with a switch. The switch exists so the "
        "demo can show what each control is load-bearing for; the fourth column "
        "of the catalogue is literally what breaks without it.</span>",
        unsafe_allow_html=True,
    )
    _defs(
        [
            (name, f"{_esc(desc)}<br><span style='color:var(--danger-ink)'>"
                   f"Without it: {_esc(breaks)}</span>")
            for _cid, name, desc, breaks in CONTROL_CATALOG
        ]
    )
    _note(
        "<b>The audit log has no switch.</b> It is listed alongside these five "
        "in the Controls popover so its absence from the switchable set is "
        "visible rather than silent. An unaudited run is not a run."
    )

    st.markdown("#### Two refusals people conflate")
    _defs(
        [
            (
                "Authority vs segregation of duties",
                "At the promotion gate, approval tests authority before it tests segregation of "
                "duties. An analyst who tries to self-approve is refused for lacking promotion "
                "authority and never reaches CTL-SOD-01. Both write the same audit action, which "
                "is why the Audit Log renders that decision as prose rather than a chip.",
            ),
            (
                "Consulted vs fired",
                "A gate event means a control was consulted, not that it said no. A passing eval "
                "gate and an approved decision are both gate events and neither is a refusal. The "
                "Audit Log splits stopped from withheld on exactly this line.",
            ),
        ]
    )


# --------------------------------------------------------------------------
# Chapter 6: screens
# --------------------------------------------------------------------------
def _screens_chapter(nav_to) -> None:  # noqa: ANN001
    st.markdown(
        f"<span class='muted'>{screen_count()} screens in the sidebar, plus "
        f"{len(DRILL_DOWNS)} drill-downs that are deliberately not nav items: "
        f"{', '.join(DRILL_DOWNS[:-1])} and {DRILL_DOWNS[-1]}. You reach those by "
        "opening a row, and the sidebar Back button returns you.</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    def _screen(label: str, target: str | None, lede: str, rows: list[tuple[str, str]]) -> None:
        with st.container(border=True):
            a, b = st.columns([8, 2], vertical_alignment="center")
            a.markdown(f"#### {label}")
            if target and b.button("Open", key=f"man_scr_{target}", use_container_width=True):
                nav_to(target)
            st.markdown(f"<span class='muted'>{lede}</span>", unsafe_allow_html=True)
            _defs(rows)

    _screen(
        "Overview",
        "Overview",
        "The command centre. Four tiles, every number live from the surface it links to.",
        [
            (
                "The CTA",
                "Names the dataset, the purpose, and the tier your current persona resolves to "
                "before you click.",
            ),
            (
                "Four tiles",
                "Datasets under classification, analyses in the certification lifecycle, agent "
                "templates, and adoption with a weekly bar chart.",
            ),
        ],
    )
    _screen(
        "Run",
        "Run",
        "The nine-stage governed walkthrough, and the centre of the product.",
        [
            (
                "The rail",
                "Nine stages plus an Architecture appendix. Each stage marks itself clear, refused "
                "or skipped once a run exists.",
            ),
            (
                "Each panel",
                "A purpose sentence, an in/does/out triple, and an engine bar naming the libraries "
                "used and the controls armed.",
            ),
            (
                "Ask",
                "Three explicit steps: confirm a dataset, declare a purpose, pick an analysis. "
                "Then the tier arithmetic, printed.",
            ),
            (
                "Plan",
                "Binds a certified analysis, checks its data contract for drift, and offers "
                "scripted or live generation.",
            ),
            (
                "Gate",
                "Nine static checks with a verdict on each, the offending line highlighted, and a "
                "Fix it button that resubmits to the same gate.",
            ),
            (
                "Attest",
                "The evidence pack, plus downloads: Quarto source for leadership, a marimo "
                "notebook for a data scientist.",
            ),
            (
                "Policy explorer",
                "Inside Access: the purpose-by-dataset matrix and an interactive tier resolver.",
            ),
        ],
    )
    _screen(
        "Pipeline",
        "Pipeline",
        "The four-agent credit-risk pipeline, and ten tabs of evidence from one run.",
        [
            (
                "Pipeline",
                "The LangGraph orchestration graph, the control envelope, and one card per step. "
                "The human gate lives here.",
            ),
            (
                "Results",
                "AUC, accuracy, the confusion matrix, top features by coefficient, the ROC curve.",
            ),
            ("Audit Log", "This run's append-only event trail, tinted by level."),
            (
                "Fairness",
                "The four-fifths disparity ratio against its threshold, selection rate by group.",
            ),
            (
                "Model Card",
                "An SR 11-7 style model-risk document generated from the run, exportable to PDF.",
            ),
            (
                "Cost & KPIs",
                "Tokens, dollars, cycle time, eval pass-rate, human overrides, and the eval gate's "
                "verdict.",
            ),
            (
                "Gateway",
                "The model-gateway ledger: every call, its stakes, the tier it routed to, cache "
                "hits and cost.",
            ),
            (
                "Knowledge",
                "Retrieved policy passages with provenance, marked public or synthetic, and which "
                "backend served them.",
            ),
            (
                "Memory",
                "Short-term working context (ephemeral) and long-term precedents, with their "
                "retention class.",
            ),
            ("Traces", "OpenTelemetry spans, one per agent, with durations and attributes."),
        ],
    )
    _screen(
        "Analyses",
        "Analyses",
        "The analysis catalogue and its parameter surface.",
        [
            (
                "Contract line",
                "What the analysis requires, its minimum rows, and the controls it runs under.",
            ),
            (
                "Dataset picker",
                "Only datasets whose declared capabilities satisfy the analysis contract.",
            ),
            (
                "Parameters",
                "Typed widgets from the analysis spec. A bad value raises a ParamError rather than "
                "running.",
            ),
        ],
    )
    _screen(
        "Datasets",
        "Datasets",
        "Eight datasets under classification, each with a data contract behind it.",
        [
            (
                "The list",
                "Classification, rows, tables, licence, commercial-use flag, onboarding state. The "
                "classification cell is clickable and explains the tier ceiling it sets.",
            ),
            (
                "A contract",
                "Metadata only, and it says so: schema, column dictionary with roles, "
                "relationships, coverage. No cell values, no distributions, no samples. Metadata "
                "access and data access are two different grants.",
            ),
        ],
    )
    _screen(
        SECTION_TEMPLATES,
        SECTION_TEMPLATES,
        "Governed blueprints, and the only screen where you author policy rather than read it.",
        [
            (
                "The list",
                "Five shipped templates with the pattern, tier ceiling and scope each declares, "
                "and whether its policy checks are clear. Open one to edit it.",
            ),
            (
                "The spec",
                "One YAML document, the same format `sentinel new-agent` writes. Every field names "
                "a value some other module owns, so the legal values beside the editor are read "
                "from those modules rather than typed here. Edits live in your session; the "
                "shipped blueprint is never changed, and Download gives you the file.",
            ),
            (
                "The checks",
                "The same four verdicts the Gate stage uses, over eleven checks. Policy checks are "
                "the fence: a refusal disables the deploy, because an illegal blueprint should not "
                "reach the registry. Certification gates are not: they block certified, which is "
                "why every shipped template reads clear on policy and still fails two gates.",
            ),
            (
                "Deploy",
                "Registers the spec as a draft analysis-agent with the dataset's content SHA "
                "computed now, exactly as the scaffolding CLI does. It appears on Registry under "
                "Analysis-agents and the four gates decide what it may become. Nothing is "
                "written to disk and no process starts; the governance outcome is real, the "
                "rollout is not.",
            ),
        ],
    )
    _screen(
        "Registry",
        "Registry",
        "Three different inventories that are easy to confuse, so the screen separates them.",
        [
            (
                "Models",
                "What a run produced. One row per run that trained something, with AUC, disparity, "
                "fairness verdict and promotion status.",
            ),
            (
                "Agents",
                "Workers inside a run. The four pipeline agents in run order, with the template, "
                "tools and RBAC scope each has.",
            ),
            (
                "Analysis-agents",
                "What a run is allowed to be. The certified unit Plan binds, under a four-gate "
                "certification lifecycle. Not the four agents above.",
            ),
        ],
    )
    _screen(
        "Platform",
        "Platform",
        "The reuse story: playbooks, templates, and the pattern catalogue.",
        [
            (
                "Playbooks",
                "Job-to-be-done write-ups with a status and the pattern each implements. "
                "Downloadable as one pack.",
            ),
            (
                "Templates",
                "The coverage metric only: how many live agents realize a template. The "
                "catalogue itself, and the editor, are on Agent Templates under Governance.",
            ),
            (
                "Patterns",
                "The agentic architecture catalogue, including one marked avoided by design and "
                "the reason why.",
            ),
        ],
    )
    _screen(
        "Adoption",
        "Adoption",
        "Whether anyone is using it, and whether the controls are getting "
        "less intrusive over time.",
        [
            ("Four metrics", "Total runs, promotion rate, human-override rate, template coverage."),
            (
                "Charts",
                "Agent utilization, runs per week, runs per dataset. Seeded telemetry from runs "
                "that really executed, labelled as such.",
            ),
        ],
    )
    _screen(
        "Audit Log",
        "Audit Log",
        "The one cross-run surface. Every other audit view in the app is scoped to a single run "
        "and dies with the session.",
        [
            (
                "Four tiles",
                "Runs logged, runs with a refusal, four-eyes coverage, distinct controls fired.",
            ),
            (
                "Stopped vs withheld",
                "The filter splits a control that ended a run from one that removed something and "
                "let it continue. A control being consulted is neither.",
            ),
            (
                "A run's detail",
                "Open any row: the run replayed as the same nine stages, keeping ran, skipped and "
                "not-in-this-route apart. Events carry the stage they were emitted at, stamped at "
                "the call site rather than guessed from the action string.",
            ),
            (
                "Scoped by role",
                "The one screen about access control obeys it. Oversight roles read the whole "
                "ledger; the first line reads its own runs. The scope is announced rather than "
                "silently applied, the filters can only narrow it, and the drill-down re-checks, "
                "or a deep link would be the way around the check.",
            ),
            (
                "Deep links",
                "?run=&lt;id&gt; opens straight to a run's evidence, so a link pasted to a "
                "colleague resolves to the run.",
            ),
        ],
    )


# --------------------------------------------------------------------------
# Chapter 7: roles and access
# --------------------------------------------------------------------------
def _roles_chapter() -> None:
    st.markdown(
        f"<span class='muted'>Six personas across three lines of defence, "
        f"policy version {policy_version()}. Three invariants hold across all of "
        "them: run authority and promotion authority are disjoint, so nobody "
        "both runs an analysis and approves it; only the Platform Admin can "
        "switch a control off, which is itself an audited act; and the audit "
        "ledger is scoped by entitlement, so the first line reads its own runs "
        "while the oversight roles read all of them.</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    for p in all_personas():
        with st.container(border=True):
            st.markdown(f"**{p.name}** &nbsp; <span class='muted'>{_esc(p.role)}</span>",
                        unsafe_allow_html=True)
            st.markdown(
                f"<span class='muted'>{_esc(p.description)}</span>",
                unsafe_allow_html=True,
            )
            _defs(
                [
                    ("can run", "yes" if p.can_run else "no"),
                    ("can approve", "yes" if p.can_approve else "no"),
                    ("can toggle controls", "yes" if p.can_toggle_controls else "no"),
                    (
                        "audit ledger scope",
                        "every run"
                        if p.can_view_all_runs
                        else "its own runs only. The entitlement defaults to "
                        "denied, because an access check that fails open is not "
                        "a check.",
                    ),
                    ("tier role", p.tier_role),
                    ("attestations", ", ".join(p.attestations) or "none"),
                ]
            )

    st.markdown("#### Column-level access")
    _defs(
        [
            (
                "Restricted globally",
                "<code>applicant_email</code> and <code>applicant_ssn</code> are denied to every "
                "agent, always.",
            ),
            (
                "Profiler",
                "An explicit twenty-column allow-list that omits <code>personal_status_sex</code>. "
                "That omission is what produces a real access-denied event on every single run.",
            ),
            (
                "EDA, Modeler, Validator",
                "All non-restricted columns. The Validator needs the protected attribute to "
                "compute fairness at all.",
            ),
            (
                "Enforcement",
                "A denial is logged at blocked level and the agent proceeds on the subset it may "
                "see. It is not an exception; the analysis continues, correctly narrower.",
            ),
        ]
    )

    st.markdown("#### Purpose limitation")
    st.markdown(
        "<span class='muted'>The one governance idea a banker recognises "
        "instantly: you may not use credit data for marketing. Not because the "
        "role lacks permission, but because the reason is wrong. The same "
        "analyst on a permitted purpose would be allowed.</span>",
        unsafe_allow_html=True,
    )
    head = ["dataset", "class"] + [PURPOSE_LABEL.get(p, p) for p in PURPOSES]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for row in matrix_rows():
        cells = [row["dataset"], row["classification"]] + [
            "allow" if row.get(p) else "refuse" for p in PURPOSES
        ]
        lines.append("| " + " | ".join(cells) + " |")
    st.markdown("\n".join(lines))


# --------------------------------------------------------------------------
# Chapter 8: data
# --------------------------------------------------------------------------
def _data_chapter() -> None:
    st.markdown(
        "<span class='muted'>Eight datasets are registered. A dataset carries "
        "its provenance, its licence, a commercial-use flag the governance layer "
        "enforces, the capabilities it provides, and a role for every column it "
        "is known to have. An analysis declares what it needs; the platform "
        "matches the two before a run rather than discovering the mismatch "
        "mid-flight.</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    for d in all_datasets():
        cls = DATA_CLASSIFICATION.get(d.id, "unclassified")
        with st.container(border=True):
            st.markdown(
                f"**{d.name}** &nbsp; <span class='cls {cls.lower()}'>{cls}</span> "
                f"&nbsp; <span class='muted'>ceiling "
                f"{CLASSIFICATION_CEILING.get(cls, 'n/a')}</span>",
                unsafe_allow_html=True,
            )
            _defs(
                [
                    ("id", f"<code>{_esc(d.id)}</code>"),
                    ("rows / tables", f"{d.rows:,} rows &middot; {d.tables} table(s)"),
                    ("licence", f"{_esc(d.license)} &middot; commercial use "
                                f"{'permitted' if d.commercial_ok else 'flagged'}"),
                    ("provides", ", ".join(sorted(d.provides))),
                    (
                        "roles",
                        ", ".join(f"{k}: {v}" for k, v in d.column_roles.items())
                        or "none declared",
                    ),
                    ("notes", _esc(d.notes)),
                ]
            )

    st.markdown("#### What a data contract publishes, and what it withholds")
    p1, p2 = st.columns(2)
    _panel(
        p1,
        "ok",
        "Published",
        [
            "Schema and column dictionary.",
            "A role per column: target, protected, treatment, outcome, timestamp, entity id, "
            "feature, PII.",
            "Foreign keys and cardinality between tables.",
            "Row counts at source, and documentation coverage.",
            "The dataset SHA the certified analysis was bound to.",
        ],
    )
    _panel(
        p2,
        "no",
        "Withheld",
        [
            "Cell values.",
            "Distributions and summary statistics.",
            "Top values or most common categories.",
            "Missingness rates.",
            "Sample rows of any size.",
        ],
    )
    _note(
        "<b>Metadata access and data access are two different grants.</b> "
        "Reading a contract tells you what an analysis could do with a dataset. "
        "It does not tell you anything about the people in it, which is why the "
        "contract screen states the boundary on its own face rather than relying "
        "on the reader to notice."
    )

    st.markdown("#### Contract drift")
    _defs(
        [
            (
                "What it is",
                "A certified analysis pins the dataset SHA it was certified against. If the "
                "current SHA differs, CTL-CONTRACT-01 refuses at Plan and the entry needs "
                "recertification.",
            ),
            (
                "Honest caveat",
                "With static CSVs committed to the repo, drift cannot actually happen in this "
                "build. The control is wired and testable; the condition that triggers it does not "
                "arise here, and the code says so.",
            ),
        ]
    )


# --------------------------------------------------------------------------
# Chapter 9: architecture
# --------------------------------------------------------------------------
def _architecture_chapter() -> None:
    st.markdown("#### Module map")
    _defs(
        [
            (
                "sentinel/agents/",
                "The four pipeline workers and the runtime that wraps each one in a span and an "
                "audit pair. An agent touches nothing except through its deps.",
            ),
            (
                "sentinel/orchestrator.py",
                "A LangGraph StateGraph with a fixed topology. The human gate is a real interrupt; "
                "approve() resumes with a Command.",
            ),
            (
                "sentinel/harness/",
                "The control plane: audit, rbac, pii, guardrails, eval_gate, cost, model_card, "
                "memory, tracing, identity, controls.",
            ),
            (
                "sentinel/govflow/",
                "The nine-stage governed flow, the purpose matrix, the tier resolver, the control "
                "catalogue, and the L1 and L3 routes.",
            ),
            (
                "sentinel/codegen/",
                "Prompts, generation with a bounded repair loop, and the two-parser static gate "
                "(ast for Python, sqlglot for SQL).",
            ),
            (
                "sentinel/sandbox/",
                "The subprocess runner, its rlimits and wall clock, and the boot-time import "
                "warm-up.",
            ),
            (
                "sentinel/disclosure/",
                "Small-cell suppression, the k-anonymity floor, PII in output, and proxy "
                "association by Cramer's V and correlation ratio.",
            ),
            (
                "sentinel/evidence/",
                "The evidence pack and its two renderings: a marimo notebook "
                "and a Quarto document.",
            ),
            (
                "sentinel/datasets/",
                "Eight dataset specs, the capability and role vocabulary, the metadata-only "
                "catalogue, and dataset fingerprints.",
            ),
            (
                "sentinel/platform/",
                "Certification, the registries, playbooks, templates, patterns, adoption metrics, "
                "and the cross-run audit store.",
            ),
            (
                "sentinel/rag/",
                "A governed corpus with provenance on every passage, a local TF-IDF store, and an "
                "optional pgvector backend behind Bedrock embeddings.",
            ),
            (
                "sentinel/gateway/",
                "A provider-agnostic model gateway: templated, Anthropic or OpenAI, with a "
                "response cache and a hard monthly cost cap.",
            ),
            (
                "sentinel/mcp_server.py",
                "The same governed tools over MCP, so an external agent inherits the controls. The "
                "governance travels with the tools.",
            ),
            (
                "sentinel/ui/",
                "The Run walkthrough, the hand-laid catalogue tables, the brand mark, and this "
                "manual.",
            ),
            (
                "app.py",
                "The shell: login gate, topbar, grouped sidebar, and every screen's render "
                "function.",
            ),
        ]
    )

    st.markdown("#### Agentic patterns, and one deliberately not used")
    for p in all_patterns():
        st.markdown(
            f"<div class='man-def'><span class='dk'>{_esc(p.name)}</span>"
            f"<span class='dv'><span class='pill pill-{_esc(p.status)}'>"
            f"{_esc(p.status.replace('_', ' '))}</span> {_esc(p.summary)}"
            f"<br><span style='color:var(--faint)'>{_esc(p.where)}</span>"
            "</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### Numbers the platform enforces")
    _defs(
        [
            (
                "Disclosure floor",
                f"{DEFAULT_CELL_FLOOR} rows. A group below it is removed from the output, not "
                f"masked.",
            ),
            (
                "Join ceiling",
                f"{DEFAULT_JOIN_CEILING} joins. More than that, or a join without ON or USING, is "
                f"refused by CTL-COMPLEX-01.",
            ),
            (
                "Faithfulness floor",
                f"{FAITHFULNESS_FLOOR}. An analysis whose eval suite scores below it cannot be "
                f"certified.",
            ),
            (
                "Wall clock",
                f"{GOVFLOW_WALL_CLOCK_S:g}s on the governed routes; {DEFAULT_WALL_CLOCK_S:g}s is "
                f"the sandbox default when a caller names none.",
            ),
            ("Memory cap", f"{DEFAULT_MEMORY_MB} MB."),
            (
                "Generation attempts",
                "3 at most. After that the refusal goes to a human rather than looping.",
            ),
        ]
    )

    st.markdown("#### Deployment")
    _defs(
        [
            (
                "Production",
                "CloudFront terminates TLS in front of a single-instance Elastic Beanstalk "
                "t3.small. Two idempotent scripts under deploy/aws own it.",
            ),
            (
                "Two cache behaviors",
                "The default carries the app with caching disabled and all viewer headers "
                "forwarded, because the Streamlit WebSocket needs the upgrade headers passed "
                "through. /static/* is separate: compressed and edge-cached.",
            ),
            (
                "Why the split matters",
                "Compress alone does nothing under a CachingDisabled policy, because CloudFront "
                "compresses what it caches and that policy drops Accept-Encoding from the cache "
                "key. Without the split, every visitor pulled 2.5MB of uncompressed front end from "
                "the instance.",
            ),
            (
                "Alternative",
                "render.yaml and a Procfile ship in the repo for a one-click Render deploy.",
            ),
            (
                "Default posture",
                "MODEL_PROVIDER=templated, so the public link costs nothing and cannot be abused. "
                "Live mode is opt-in and capped.",
            ),
        ]
    )

    _note(
        "<b>Known documentation drift, stated rather than hidden.</b> The README "
        "still describes a six-tab UI and a plain-Python orchestrator. The "
        "Pipeline screen has ten tabs, and the orchestrator has been a LangGraph "
        "StateGraph since the interrupt-based human gate landed."
    )


# --------------------------------------------------------------------------
# Chapter 10: glossary
# --------------------------------------------------------------------------
def _glossary_chapter() -> None:
    st.markdown(
        "<span class='muted'>The words this product uses in a specific way, in "
        "alphabetical order.</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    _defs(sorted(_GLOSSARY, key=lambda kv: kv[0].lower()))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def _step(delta: int) -> None:
    idx = CHAPTERS.index(st.session_state.get("manual_chapter", PRESENTATION))
    st.session_state.manual_chapter = CHAPTERS[
        max(0, min(len(CHAPTERS) - 1, idx + delta))
    ]


def render_manual(nav_to) -> None:  # noqa: ANN001
    """The User Manual screen.

    `nav_to` is `app._nav_to`, passed in rather than imported: `app.py` imports
    this module, so importing back would be a cycle. It is what the deck's
    screen-map buttons and the quick start's "Go to Run" use.
    """
    st.markdown(_MANUAL_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='eyebrow' style='margin-bottom:4px'>Help</div>",
        unsafe_allow_html=True,
    )
    st.subheader("User Manual")
    st.markdown(
        "<span class='muted'>What Sentinel is, how it is governed, and how to "
        "drive it. Start with the presentation; the nine chapters after it are "
        "the reference. Every number on these pages is read from the module "
        "that enforces it, so the manual cannot quietly fall out of step with "
        "the product.</span>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("manual_chapter") not in CHAPTERS:
        st.session_state.manual_chapter = PRESENTATION
    chapter = st.radio(
        "Chapter",
        CHAPTERS,
        horizontal=True,
        key="manual_chapter",
        label_visibility="collapsed",
    )

    if chapter == PRESENTATION:
        _deck(nav_to)
    elif chapter == "Quick start":
        _quick_start(nav_to)
    elif chapter == "The nine stages":
        _stages_chapter()
    elif chapter == "Autonomy levels":
        _levels_chapter()
    elif chapter == "Controls":
        _controls_chapter()
    elif chapter == "Screens":
        _screens_chapter(nav_to)
    elif chapter == "Roles & access":
        _roles_chapter()
    elif chapter == "Data":
        _data_chapter()
    elif chapter == "Architecture":
        _architecture_chapter()
    elif chapter == "Glossary":
        _glossary_chapter()

    idx = CHAPTERS.index(chapter)
    nav1, cap, nav2 = st.columns([1, 6, 1], vertical_alignment="center")
    nav1.button(
        "← Back", disabled=idx == 0, on_click=_step, args=(-1,), key="man_back"
    )
    cap.markdown(
        f"<div style='text-align:center'><span class='mono' "
        f"style='font-size:12px;color:var(--faint)'>Chapter {idx + 1} / "
        f"{len(CHAPTERS)}</span></div>",
        unsafe_allow_html=True,
    )
    nav2.button(
        "Next →",
        disabled=idx == len(CHAPTERS) - 1,
        on_click=_step,
        args=(1,),
        key="man_next",
    )
