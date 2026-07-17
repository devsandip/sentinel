"""Disclosure control: the Screen stage (section 5, Stage 7).

Disclosure control runs on the result object before anything downstream sees it,
including the language model that narrates. You cannot leak what you were never
shown, so suppression happens here, upstream of the model, not in the UI.

This is the highest-signal control on the list and the one nobody demos. The v1
done-when turns on it: an n=3 cell is suppressed before the narration model sees
the result.

Modules:
  association -- Cramer's V and correlation ratio (for CTL-PROXY-01).
  screen      -- the Screen stage: small-cell suppression (CTL-DISC-02),
                 k-anonymity floor (CTL-DISC-01), PII in output (CTL-DISC-03),
                 and proxy discovery (CTL-PROXY-01).
"""

from __future__ import annotations

from .screen import ProxyFlag, ScreenResult, SuppressedCell, find_proxies, screen

__all__ = [
    "ProxyFlag",
    "ScreenResult",
    "SuppressedCell",
    "find_proxies",
    "screen",
]
