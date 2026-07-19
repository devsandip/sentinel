"""Streamlit UI modules for surfaces too large to live in app.py.

The deploy bundle ships app.py + sentinel/, so UI code that leaves app.py must
live here. These modules are presentation only: they import the flow/tier/
control modules and render; no governance logic lives in them.
"""
