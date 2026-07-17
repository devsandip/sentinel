"""OpenLineage emission: provenance as a standards-based graph (section 12).

The provenance chain in the evidence pack is human-readable. This module emits
the same chain as OpenLineage events at Access (a START event, the input dataset
bound to its contract SHA) and Attest (a COMPLETE event, the output dataset being
the finding). Standards-based lineage is what a bank's existing tooling already
consumes, so the chain is a graph a Marquez or DataHub can ingest rather than a
bespoke table. We build conformant events and capture them in-process; there is
no lineage backend in the demo, and we do not pretend there is one.
"""

from __future__ import annotations

from .emit import NAMESPACE, run_lineage_events

__all__ = ["NAMESPACE", "run_lineage_events"]
