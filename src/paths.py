"""Artifact-root locations.

Scripts live in ``src/``; datasets and committed results live at the repository
root (``data/``, ``results/``). Import this module instead of joining paths
relative to ``__file__``.
"""
from __future__ import annotations

import os

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
