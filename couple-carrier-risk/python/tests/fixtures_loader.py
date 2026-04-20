"""Fixture loader shared between unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_json_fixture(name: str) -> dict[str, Any]:
    parsed: Any = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def fixture_path(name: str) -> Path:
    return FIXTURES / name
