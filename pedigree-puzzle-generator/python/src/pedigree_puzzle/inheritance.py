"""Inheritance-mode enum and the associated biological-sex enum.

Kept separate from :mod:`puzzle_blueprint` so the pure domain vocabulary
has nothing to do with pedigree-building mechanics -- answer_explainer
and mode_heuristics both depend on this, but not on each other.
"""

from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    AD = "AD"
    AR = "AR"
    XLR = "XLR"
    XLD = "XLD"
    MT = "MT"

    @property
    def full_name(self) -> str:
        return _FULL_NAMES[self]


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


_FULL_NAMES: dict[Mode, str] = {
    Mode.AD: "Autosomal Dominant",
    Mode.AR: "Autosomal Recessive",
    Mode.XLR: "X-linked Recessive",
    Mode.XLD: "X-linked Dominant",
    Mode.MT: "Mitochondrial",
}
