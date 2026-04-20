"""Declares the three BayesMendel models this demo compares.

Keeping the registry in one place means adding a fourth model is a
one-line edit — no presenter, no builder, no client needs to change.
"""

from __future__ import annotations

BAYESMENDEL_MODELS: tuple[str, ...] = ("BRCAPRO", "MMRpro", "PancPRO")
