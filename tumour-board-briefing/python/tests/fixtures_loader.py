"""Fixture loader shared between unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_json(name: str) -> dict[str, Any]:
    parsed: Any = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def load_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def load_all_risk_fixtures() -> dict[str, dict[str, Any]]:
    return {
        "CLAUS": load_json("sample-risk-claus"),
        "COUCH": load_json("sample-risk-couch"),
        "FRANK": load_json("sample-risk-frank"),
        "MANCHESTER": load_json("sample-risk-manchester"),
        "NICE": load_json("sample-risk-nice"),
        "TYRER_CUZICK": load_json("sample-risk-tc"),
    }
