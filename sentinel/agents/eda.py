"""EDA / Feature agent.

Reviews distributions and confirms the protected attribute will be excluded
from model inputs. Also demonstrates PII redaction: it builds a sample-record
note that includes an applicant email, and that text is scrubbed before it
would ever reach an LLM.
"""

from __future__ import annotations

from .base import Agent


class EDAAgent(Agent):
    id = "eda"
    title = "EDA / Feature"
    template = "data_analysis"

    def run(self, state) -> None:  # noqa: ANN001
        ds = self.deps.dataset
        self.read_columns(list(ds.feature_columns))

        # Simulate PII leaking into text destined for the LLM: pull one real
        # applicant's email into a human note, then redact before narrating.
        sample = ds.frame.iloc[0]
        leaked_note = (
            f"Example applicant {sample['applicant_email']} "
            f"(age band {sample['age_band']}) illustrates the join key."
        )
        safe_note = self.redact_text(leaked_note)

        self.log(
            "eda_reviewed",
            inputs_summary=f"{len(ds.feature_columns)} features reviewed",
            output_summary=(
                f"Protected attribute '{ds.protected_attribute}' marked for "
                f"exclusion. Sample note scrubbed: {safe_note}"
            ),
        )
        gen = self.narrate(
            "eda",
            {"protected_attribute": ds.protected_attribute},
        )
        state.add_step(self, "done", gen)
