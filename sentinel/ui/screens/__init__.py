"""One module per sidebar screen.

Split out of a 3,200 line `app.py` on 2026-07-21. The file had become the
thing blocking parallel work: any second branch touching a screen touched
`app.py`, and by the time anyone returned to it the branch was unmergeable.
"""
