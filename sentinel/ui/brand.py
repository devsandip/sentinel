"""The Sentinel mark, in one place.

Two surfaces draw it: the login gate and the topbar lockup in `app.py`, and the
User Manual's cover slide (`sentinel/ui/manual.py`). It lived as a private
constant in `app.py` until the manual needed it; a second copy of a logo is the
kind of duplication that goes stale silently, so it moved here rather than
being pasted.
"""

from __future__ import annotations

SHIELD_SVG = (
    "<svg viewBox='0 0 24 24' aria-hidden='true'>"
    "<path d='M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5z' fill='#1e50a0'/>"
    "<path d='M8 12l3 3 5-6' fill='none' stroke='#fff' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'/></svg>"
)
