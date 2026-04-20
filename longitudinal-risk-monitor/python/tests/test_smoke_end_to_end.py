"""End-to-end smoke walk using fake Evagene responses.

Exercises the CLI exactly as described in the README's "Live smoke"
section — seed, run (no-op), forge a mismatched baseline, re-run (one
notification), inspect history, delete the DB.  A real API key is not
available in this environment, so the Evagene client is swapped for a
fake that replays the shipped NICE fixtures.
"""

from __future__ import annotations

import io
import json
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from longitudinal_risk_monitor import app as app_module
from longitudinal_risk_monitor.evagene_client import PedigreeSummary

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _load(name: str) -> dict[str, Any]:
    payload: Any = json.loads((_FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _pedigrees() -> list[dict[str, Any]]:
    raw = json.loads((_FIXTURES / "sample-list-pedigrees.json").read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    return raw


class _FakeEvageneClient:
    def __init__(self, payloads: dict[str, dict[str, Any]], listing: list[PedigreeSummary]) -> None:
        self._payloads = payloads
        self._listing = listing

    def list_pedigrees(self) -> list[PedigreeSummary]:
        return list(self._listing)

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]:
        return self._payloads[pedigree_id]


class _FakeGateway:
    """Satisfies HttpxGateway interface; records outbound Slack posts."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def get_json(self, url: str, *, headers: dict[str, str]) -> Any:  # pragma: no cover
        del url, headers
        raise AssertionError("Fake gateway should not receive GETs in this smoke test.")

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> Any:
        del headers
        self.posts.append((url, body))

        class _Response:
            status_code = 200

            def json(self) -> Any:
                return {}

        return _Response()

    def close(self) -> None:
        return None


@pytest.fixture()
def wired(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, Any]]:
    pedigrees = _pedigrees()
    listing = [PedigreeSummary(p["id"], p["display_name"]) for p in pedigrees]
    green, amber, red = (
        _load("sample-nice-green.json"),
        _load("sample-nice-amber.json"),
        _load("sample-nice-red.json"),
    )
    payloads = {
        pedigrees[0]["id"]: green,
        pedigrees[1]["id"]: green,
        pedigrees[2]["id"]: green,
        pedigrees[3]["id"]: amber,
        pedigrees[4]["id"]: red,
    }

    def _make_client(**_: Any) -> _FakeEvageneClient:
        return _FakeEvageneClient(payloads, listing)

    gateway = _FakeGateway()
    monkeypatch.setattr(app_module, "EvageneClient", _make_client)
    monkeypatch.setattr(app_module, "HttpxGateway", lambda: gateway)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    db = tmp_path / "smoke.db"
    monkeypatch.setenv("EVAGENE_API_KEY", "evg_smoke")
    monkeypatch.setenv("RISK_MONITOR_DB", str(db))
    yield {"db": db, "pedigrees": pedigrees, "gateway": gateway}


def test_step1_seed_populates_baseline_without_notifications(wired: dict[str, Any]) -> None:
    out, err = io.StringIO(), io.StringIO()

    rc = app_module.run(["seed"], out, err)

    assert rc == 0
    assert "Seeded baseline for 5 pedigree(s)." in out.getvalue()
    assert err.getvalue() == ""


def test_step2_run_with_no_changes_reports_zero(wired: dict[str, Any]) -> None:
    app_module.run(["seed"], io.StringIO(), io.StringIO())

    out, err = io.StringIO(), io.StringIO()
    rc = app_module.run(["run"], out, err)

    assert rc == 0
    assert "0 change(s) detected" in out.getvalue()


def test_step3_forged_baseline_triggers_stdout_notification(wired: dict[str, Any]) -> None:
    app_module.run(["seed"], io.StringIO(), io.StringIO())
    target = wired["pedigrees"][3]["id"]
    with sqlite3.connect(wired["db"]) as direct:
        direct.execute(
            """
            UPDATE pedigree_nice_state
            SET category = ?, triggers_json = ?
            WHERE pedigree_id = ?
            """,
            ("near_population", "[]", target),
        )
        direct.commit()

    out, err = io.StringIO(), io.StringIO()
    rc = app_module.run(["run"], out, err)

    assert rc == 1
    produced = out.getvalue()
    assert "Davies family (moderate-risk): NEAR_POPULATION -> MODERATE" in produced
    assert "1 change(s) detected" in produced


def test_step3b_slack_channel_posts_single_attachment_payload(wired: dict[str, Any]) -> None:
    app_module.run(["seed"], io.StringIO(), io.StringIO())
    target = wired["pedigrees"][3]["id"]
    with sqlite3.connect(wired["db"]) as direct:
        direct.execute(
            """
            UPDATE pedigree_nice_state
            SET category = ?, triggers_json = ?
            WHERE pedigree_id = ?
            """,
            ("near_population", "[]", target),
        )
        direct.commit()

    rc = app_module.run(
        ["run", "--channel", "slack-webhook", "--channel-arg", "https://hooks.example/X"],
        io.StringIO(),
        io.StringIO(),
    )

    assert rc == 1
    gateway: _FakeGateway = wired["gateway"]
    assert len(gateway.posts) == 1
    posted_url, posted_body = gateway.posts[0]
    assert posted_url == "https://hooks.example/X"
    assert posted_body["attachments"][0]["color"] == "warning"
    assert "Davies family (moderate-risk)" in posted_body["text"]


def test_step4_history_lists_the_injected_event(wired: dict[str, Any]) -> None:
    app_module.run(["seed"], io.StringIO(), io.StringIO())
    target = wired["pedigrees"][3]["id"]
    with sqlite3.connect(wired["db"]) as direct:
        direct.execute(
            """
            UPDATE pedigree_nice_state
            SET category = ?, triggers_json = ?
            WHERE pedigree_id = ?
            """,
            ("near_population", "[]", target),
        )
        direct.commit()
    app_module.run(["run"], io.StringIO(), io.StringIO())

    out, err = io.StringIO(), io.StringIO()
    rc = app_module.run(["history"], out, err)

    assert rc == 0
    listed = out.getvalue()
    assert target in listed
    assert "near_population -> moderate" in listed
