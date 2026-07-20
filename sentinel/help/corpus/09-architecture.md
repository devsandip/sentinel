---
id: architecture
title: Architecture
chapter: Architecture
summary: The module map, the agentic patterns in use and the one avoided, the bought-versus-built split, where the enforced numbers live, and how the app is deployed.
---

## The module map

The agents package holds the pipeline workers and the runtime that wraps each one in a trace span and an audit pair. An agent touches nothing except through its declared dependencies, which is what makes the audit trail complete by construction.

The orchestrator module is a LangGraph StateGraph with a fixed topology. The human gate inside it is a real interrupt rather than a boolean flag: the graph stops at the gate, and approval resumes it with a Command.

The govflow package is the nine-stage governed flow. govflow holds the purpose matrix, the tier resolver, the control catalogue and the L1 and L3 routes, and it is where a governed run's shape is defined.

The codegen package holds the prompts, generation with a bounded repair loop, and the two-parser static gate. The Python half of the gate uses ast and the SQL half uses sqlglot, and neither parser executes what it reads.

The sandbox package holds the subprocess runner, its resource limits and wall clock, and the boot-time import warm-up. The disclosure package holds small-cell suppression, the anonymity floor, PII detection in output, and proxy association measured by Cramer's V and the correlation ratio.

The platform package holds certification, the registries, playbooks, templates, patterns, adoption metrics and the cross-run audit store. The rag package holds a governed corpus with provenance on every passage, a local TF-IDF store and an optional pgvector backend behind managed embeddings.

The ui package holds the Run walkthrough, the hand-laid catalogue tables, the brand mark and the User Manual itself. The app module is the shell: the login gate, the topbar, the grouped sidebar and every screen's render function.

## Agentic patterns

Evaluator-optimizer is in use. The bounded repair loop in codegen is an evaluator-optimizer: the static gate evaluates, the model repairs, and the repaired code faces the same gate rather than a relaxed one.

Orchestrator-workers is marked avoided by design, with the reason written into the catalogue. A pattern where the orchestrator decomposes the task at runtime produces a control flow that cannot be reviewed in advance, and a fixed topology is worth more to this product than dynamic decomposition.

## Bought versus built

The maths is bought and the governance is built. Every library listed as bought actually runs in this build, and where a package is installed only so the sandbox can honour an import grant, the row says so rather than implying the package is load-bearing.

The bought side covers Streamlit for every screen, pandas and numpy for the data plane at Access, Execute and Screen, duckdb for gated SQL over policy-scoped frames, sqlglot for the SQL half of the static gate, and Python's own ast for the Python half. It also covers scikit-learn for the baseline model and its metrics, fairlearn for group fairness metrics and the disparity ratio, and statsmodels, lifelines, shap, dowhy and econml, which are on the import allowlists so that generated code can reach for them.

The bought side further covers LangGraph for the orchestrator's StateGraph and its interrupt, the OpenTelemetry SDK for one span per agent, the OpenLineage client for provenance events at Access and Attest, fpdf2 for the model card PDF, and the Anthropic client for live narration and live codegen behind a monthly cost cap. Quarto and marimo are external tools rather than Python distributions, and the evidence pack ships its Quarto source and says so plainly when Quarto is absent.

The built side is the governance itself: the static gate, the sandbox, the disclosure screen, the purpose matrix and tier resolver, the control catalogue, the audit log and cross-run ledger, RBAC and PII and guardrails and the eval gate and cost, the certification lifecycle, the dataset registry and data contracts, the evidence pack and its two outputs, the model gateway and the MCP server.

Some names appear on the dependency map but are not wired into this build, and they are labelled roadmap rather than claimed. Presidio, Evidently, OPA and pandera are on that list.

## Where the enforced numbers live

Every number the product enforces reads from the module that enforces it, and the Architecture chapter of the User Manual prints those numbers in one place. The disclosure floor comes from the disclosure screen module. The SQL join ceiling comes from the SQL gate module. The faithfulness floor comes from the certification module. The wall clock and the memory cap come from the sandbox execute module, and the generation attempt limit comes from codegen.

Naming the number in the module that enforces it is what makes a doc-versus-code drift impossible to hide. The repo has paid for the alternative twice: an import allowlist that named packages installed nowhere, and an Execute panel whose stated wall clock had not matched the enforced one for several versions.

## Deployment

Production runs behind CloudFront, which terminates TLS in front of a single-instance Elastic Beanstalk environment on a small instance type. Two idempotent scripts under the deploy directory own the infrastructure, so a redeploy is a rerun rather than a manual sequence.

CloudFront carries two cache behaviors. The default behavior carries the app with caching disabled and all viewer headers forwarded, because the Streamlit WebSocket needs the upgrade headers passed through. The static path is separate: compressed and edge-cached.

An alternative deployment ships in the repo: a render.yaml and a Procfile for a one-click Render deploy. The default posture is the templated model provider, so the public link costs nothing and cannot be abused, and live model mode is opt-in and capped.

Known documentation drift is stated rather than hidden. The README still describes an older tab count for the user interface and a plain-Python orchestrator, and neither is true: the Pipeline screen has grown its tab set, and the orchestrator has been a LangGraph StateGraph since the interrupt-based human gate landed.
