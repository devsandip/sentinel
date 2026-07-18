"""Build OpenLineage events for one governed run.

Two events per run: a START at Access (the input dataset, bound to its contract
SHA via a DatasetVersion facet) and a COMPLETE at Attest (the output dataset, the
finding). Events are built with the OpenLineage client so they are schema-valid,
then serialized to dicts and captured; the demo has no lineage backend, so we do
not emit to one.
"""

from __future__ import annotations

import uuid

from openlineage.client.event_v2 import (
    InputDataset,
    Job,
    OutputDataset,
    Run,
    RunEvent,
    RunState,
)
from openlineage.client.facet_v2 import (
    dataset_version_dataset,
    documentation_dataset,
)
from openlineage.client.serde import Serde

NAMESPACE = "sentinel"


def _run_uuid(run_id: str) -> str:
    """A valid, deterministic OpenLineage runId derived from our 12-hex run id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, run_id))


def _input_dataset(dataset: str, dataset_sha: str | None, purpose: str) -> InputDataset:
    facets: dict = {
        "documentation": documentation_dataset.DocumentationDatasetFacet(
            description=f"{purpose} scoped view"
        ),
    }
    if dataset_sha:
        facets["version"] = dataset_version_dataset.DatasetVersionDatasetFacet(
            datasetVersion=dataset_sha
        )
    return InputDataset(namespace=NAMESPACE, name=dataset, facets=facets)


def _output_dataset(purpose: str, finding: str) -> OutputDataset:
    return OutputDataset(
        namespace=NAMESPACE,
        name=f"evidence.{purpose}",
        facets={
            "documentation": documentation_dataset.DocumentationDatasetFacet(
                description=finding
            ),
        },
    )


def run_lineage_events(
    *,
    run_id: str,
    purpose: str,
    dataset: str,
    dataset_sha: str | None,
    finding: str,
    started_at: str,
    completed_at: str,
) -> list[dict]:
    """Return the START (Access) and COMPLETE (Attest) events as schema-valid dicts.

    On any construction error the function returns an empty list: lineage is
    evidence, not a control, so a lineage hiccup must never break a governed run.
    """
    try:
        run = Run(runId=_run_uuid(run_id))
        job = Job(namespace=NAMESPACE, name=f"govflow.{purpose}")
        inp = _input_dataset(dataset, dataset_sha, purpose)
        out = _output_dataset(purpose, finding)
        start = RunEvent(
            eventType=RunState.START,
            eventTime=started_at,
            run=run,
            job=job,
            inputs=[inp],
            outputs=[],
        )
        complete = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=completed_at,
            run=run,
            job=job,
            inputs=[inp],
            outputs=[out],
        )
        return [Serde.to_dict(start), Serde.to_dict(complete)]
    except Exception:  # noqa: BLE001 - lineage must never break the run
        return []
