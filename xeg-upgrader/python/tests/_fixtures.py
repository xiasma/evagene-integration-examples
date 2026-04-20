"""Fixture-file helpers shared by the test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def fixture_path(name: str) -> Path:
    return _FIXTURES / name


def fixture_text(name: str) -> str:
    return fixture_path(name).read_text(encoding="utf-8")


def fixture_json(name: str) -> dict[str, Any]:
    data = json.loads(fixture_text(name))
    if not isinstance(data, dict):
        raise TypeError(f"expected dict in {name}, got {type(data).__name__}")
    return data
