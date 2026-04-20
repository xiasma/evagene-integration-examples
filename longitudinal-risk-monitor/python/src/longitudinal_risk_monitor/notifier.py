"""Notifier abstraction and the three concrete channels the CLI exposes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TextIO

from .evaluator import ChangeEvent
from .http_gateway import PostGateway


@dataclass(frozen=True)
class Notification:
    event: ChangeEvent
    pedigree_label: str


class Notifier(Protocol):
    def notify(self, notification: Notification) -> None: ...


class StdoutNotifier:
    """Write a single human-readable line per change to the injected sink."""

    def __init__(self, sink: TextIO) -> None:
        self._sink = sink

    def notify(self, notification: Notification) -> None:
        self._sink.write(format_line(notification) + "\n")


class FileNotifier:
    """Append one human-readable line per change to a log file."""

    def __init__(self, path: str) -> None:
        self._path = path

    def notify(self, notification: Notification) -> None:
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(format_line(notification) + "\n")


class SlackWebhookNotifier:
    """POST a Slack incoming-webhook payload per change.

    The payload uses Slack's legacy ``attachments`` block for colour —
    it works with every incoming-webhook URL without requiring a Block
    Kit-capable workspace config.
    """

    def __init__(self, webhook_url: str, http: PostGateway) -> None:
        self._webhook_url = webhook_url
        self._http = http

    def notify(self, notification: Notification) -> None:
        self._http.post_json(
            self._webhook_url,
            headers={"Content-Type": "application/json"},
            body=build_slack_payload(notification),
        )


def format_line(notification: Notification) -> str:
    event = notification.event
    old = event.old_category.upper()
    new = event.new_category.upper()
    label = notification.pedigree_label or event.pedigree_id
    parts = [f"{label}: {old} -> {new}"]
    if event.triggers_added:
        parts.append("added: " + "; ".join(event.triggers_added))
    if event.triggers_removed:
        parts.append("removed: " + "; ".join(event.triggers_removed))
    return " | ".join(parts)


def build_slack_payload(notification: Notification) -> dict[str, Any]:
    event = notification.event
    label = notification.pedigree_label or event.pedigree_id
    old = event.new_category
    colour = _SLACK_COLOUR_BY_CATEGORY.get(old, "#cccccc")
    fields: list[dict[str, Any]] = []
    if event.triggers_added:
        fields.append(
            {"title": "Triggers added", "value": "\n".join(event.triggers_added), "short": False},
        )
    if event.triggers_removed:
        fields.append(
            {
                "title": "Triggers removed",
                "value": "\n".join(event.triggers_removed),
                "short": False,
            },
        )
    return {
        "text": (
            f"NICE category change for *{label}*: "
            f"`{event.old_category}` -> `{event.new_category}`"
        ),
        "attachments": [
            {
                "color": colour,
                "title": label,
                "text": (
                    f"Category changed from {event.old_category} to {event.new_category}."
                ),
                "fields": fields,
            },
        ],
    }


_SLACK_COLOUR_BY_CATEGORY: dict[str, str] = {
    "near_population": "good",
    "moderate": "warning",
    "high": "danger",
}
