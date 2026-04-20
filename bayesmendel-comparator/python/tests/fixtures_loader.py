"""Fixture loader shared between unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    parsed: Any = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def load_all_fixtures() -> dict[str, dict[str, Any]]:
    return {
        "BRCAPRO": load_fixture("sample-brcapro"),
        "MMRpro": load_fixture("sample-mmrpro"),
        "PancPRO": load_fixture("sample-pancpro"),
    }
