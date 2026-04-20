import io
import json
from pathlib import Path
from typing import Any

from longitudinal_risk_monitor.evaluator import ChangeEvent
from longitudinal_risk_monitor.notifier import (
    FileNotifier,
    Notification,
    SlackWebhookNotifier,
    StdoutNotifier,
    build_slack_payload,
    format_line,
)

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"


def _amber_notification() -> Notification:
    event = ChangeEvent(
        pedigree_id=_PEDIGREE_ID,
        old_category="near_population",
        new_category="moderate",
        triggers_added=("Single first-degree relative with breast cancer <40.",),
        triggers_removed=(),
    )
    return Notification(event=event, pedigree_label="Ashton family")


def test_format_line_lists_category_shift_and_added_triggers() -> None:
    line = format_line(_amber_notification())

    assert "Ashton family: NEAR_POPULATION -> MODERATE" in line
    assert "added: Single first-degree relative with breast cancer <40." in line


def test_format_line_falls_back_to_pedigree_id_when_label_missing() -> None:
    event = ChangeEvent(_PEDIGREE_ID, "moderate", "high", (), ())
    line = format_line(Notification(event=event, pedigree_label=""))

    assert _PEDIGREE_ID in line


def test_stdout_notifier_writes_one_line() -> None:
    sink = io.StringIO()

    StdoutNotifier(sink).notify(_amber_notification())

    output = sink.getvalue()
    assert output.endswith("\n")
    assert "Ashton family" in output


def test_file_notifier_appends_across_invocations(tmp_path: Path) -> None:
    path = tmp_path / "monitor.log"

    notifier = FileNotifier(str(path))
    notifier.notify(_amber_notification())
    notifier.notify(_amber_notification())

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


class _RecordingPostGateway:
    def __init__(self) -> None:
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}
        self.last_body: dict[str, Any] = {}

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> Any:
        self.last_url = url
        self.last_headers = headers
        self.last_body = body

        class _Response:
            status_code = 200

            def json(self) -> Any:
                return {}

        return _Response()


def test_slack_webhook_notifier_posts_to_configured_url() -> None:
    gateway = _RecordingPostGateway()

    SlackWebhookNotifier("https://hooks.example/X", gateway).notify(_amber_notification())

    assert gateway.last_url == "https://hooks.example/X"
    assert gateway.last_headers["Content-Type"] == "application/json"
    assert isinstance(gateway.last_body, dict)


def test_slack_payload_carries_attachment_with_category_colour() -> None:
    payload = build_slack_payload(_amber_notification())

    assert "NICE category change" in payload["text"]
    attachments = payload["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["color"] == "warning"
    fields = attachments[0]["fields"]
    assert any(field["title"] == "Triggers added" for field in fields)


def test_slack_payload_is_valid_json_serialisable() -> None:
    payload = build_slack_payload(_amber_notification())

    round_trip = json.loads(json.dumps(payload))
    assert round_trip["attachments"][0]["color"] == "warning"


def test_slack_payload_uses_danger_colour_when_new_category_high() -> None:
    event = ChangeEvent(_PEDIGREE_ID, "moderate", "high", ("New trigger.",), ())
    payload = build_slack_payload(Notification(event=event, pedigree_label="Evans family"))

    assert payload["attachments"][0]["color"] == "danger"
