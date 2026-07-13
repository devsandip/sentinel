"""OpenTelemetry tracing (ideas.md item 8).

Every agent step and gateway call emits an OpenTelemetry span, tagged with the
run id, nested under the run. Spans are captured in-process by a custom span
processor so the UI can render the trace tree for a run; an OTLP exporter can be
added for a real backend (Jaeger, Tempo, Honeycomb) without touching call sites.
OpenTelemetry is the recognized tracing standard, so this is the observability
layer a bank panel will know.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider

_RUN_ID_ATTR = "sentinel.run_id"

# Captured spans, keyed by run id, in end order.
_SPANS: dict[str, list[dict[str, Any]]] = {}


class _Collector(SpanProcessor):
    """Appends each finished span to the per-run collection for the UI."""

    def on_start(self, span, parent_context=None) -> None:  # noqa: ANN001
        return None

    def on_end(self, span: ReadableSpan) -> None:
        run_id = span.attributes.get(_RUN_ID_ATTR) if span.attributes else None
        if not run_id:
            return
        _SPANS.setdefault(str(run_id), []).append(
            {
                "name": span.name,
                "duration_ms": round((span.end_time - span.start_time) / 1e6, 2),
                "start_ns": span.start_time,
                "attributes": {
                    k: v for k, v in (span.attributes or {}).items() if k != _RUN_ID_ATTR
                },
            }
        )

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


_provider = TracerProvider()
_provider.add_span_processor(_Collector())
# Set the global provider once; ignore if the host app already set one.
try:
    trace.set_tracer_provider(_provider)
except Exception:  # noqa: BLE001
    pass
_tracer = trace.get_tracer("sentinel")


@contextmanager
def span(name: str, run_id: str, **attributes: Any):
    """Open a span tagged with the run id and the given attributes."""
    with _tracer.start_as_current_span(name) as s:
        s.set_attribute(_RUN_ID_ATTR, run_id)
        for k, v in attributes.items():
            if v is not None:
                s.set_attribute(k, v)
        yield s


def spans_for(run_id: str) -> list[dict[str, Any]]:
    """Captured spans for a run, ordered by start time."""
    return sorted(_SPANS.get(run_id, []), key=lambda s: s["start_ns"])
