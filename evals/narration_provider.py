"""promptfoo custom provider: routes a prompt through the Sentinel gateway.

promptfoo calls `call_api(prompt, options, context)`. We ignore the prompt text
and use the test `vars` (step + context) to drive `ModelGateway.narrate` in
scripted mode, so the eval exercises the real gateway code path at zero cost.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Make the repo root importable when promptfoo loads this provider from evals/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.gateway.model_gateway import ModelGateway  # noqa: E402


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]):
    variables = (context or {}).get("vars", {})
    step = variables.get("step", "profiler")
    ctx = variables.get("context", {})
    if isinstance(ctx, str):
        ctx = json.loads(ctx)
    gen = ModelGateway(provider="templated").narrate(step, ctx)
    return {"output": gen.text}
