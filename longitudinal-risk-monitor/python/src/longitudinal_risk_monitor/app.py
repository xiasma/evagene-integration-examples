"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from typing import TextIO

from .config import (
    Channel,
    ConfigError,
    HistoryConfig,
    RunConfig,
    SeedConfig,
    load_config,
)
from .evagene_client import ApiError, EvageneClient
from .history_presenter import present as present_history
from .http_gateway import HttpxGateway
from .notifier import FileNotifier, Notifier, SlackWebhookNotifier, StdoutNotifier
from .orchestrator import Orchestrator, RunSummary
from .state_store import StateStore

EXIT_OK = 0
EXIT_CHANGES_DETECTED = 1
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69


class _SystemClock:
    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    if isinstance(config, HistoryConfig):
        return _dispatch_history(config, stdout)
    gateway = HttpxGateway()
    try:
        if isinstance(config, RunConfig):
            return _dispatch_run(config, gateway, stdout, stderr)
        if isinstance(config, SeedConfig):
            return _dispatch_seed(config, gateway, stdout, stderr)
    finally:
        gateway.close()
    raise AssertionError("unreachable")


def _dispatch_history(config: HistoryConfig, stdout: TextIO) -> int:
    store = StateStore(config.sqlite_path)
    try:
        events = store.list_events(config.pedigree_id)
        present_history(events, config.format, stdout)
    finally:
        store.close()
    return EXIT_OK


def _dispatch_run(
    config: RunConfig,
    gateway: HttpxGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    notifier = _build_notifier(config.channel, config.channel_arg, gateway, stdout)
    store = StateStore(config.sqlite_path)
    try:
        orchestrator = Orchestrator(
            source=_build_client(config.credentials.base_url, config.credentials.api_key, gateway),
            store=store,
            notifier=notifier,
            clock=_SystemClock(),
            sleep=time.sleep,
            dry_run=config.dry_run,
        )
        try:
            summary = orchestrator.run()
        except ApiError as error:
            stderr.write(f"error: {error}\n")
            return EXIT_UNAVAILABLE
        _write_summary(summary, stdout)
    finally:
        store.close()
    return EXIT_CHANGES_DETECTED if summary.changes_detected > 0 else EXIT_OK


def _dispatch_seed(
    config: SeedConfig,
    gateway: HttpxGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    store = StateStore(config.sqlite_path)
    try:
        orchestrator = Orchestrator(
            source=_build_client(config.credentials.base_url, config.credentials.api_key, gateway),
            store=store,
            notifier=_NullNotifier(),
            clock=_SystemClock(),
            sleep=time.sleep,
            dry_run=False,
        )
        try:
            summary = orchestrator.seed()
        except ApiError as error:
            stderr.write(f"error: {error}\n")
            return EXIT_UNAVAILABLE
        stdout.write(f"Seeded baseline for {summary.pedigrees_checked} pedigree(s).\n")
    finally:
        store.close()
    return EXIT_OK


def _build_client(base_url: str, api_key: str, gateway: HttpxGateway) -> EvageneClient:
    return EvageneClient(
        base_url=base_url,
        api_key=api_key,
        http_get=gateway,
        http_post=gateway,
        sleep=time.sleep,
    )


def _build_notifier(
    channel: Channel,
    channel_arg: str | None,
    gateway: HttpxGateway,
    stdout: TextIO,
) -> Notifier:
    if channel is Channel.STDOUT:
        return StdoutNotifier(stdout)
    if channel is Channel.FILE:
        assert channel_arg is not None
        return FileNotifier(channel_arg)
    assert channel is Channel.SLACK_WEBHOOK
    assert channel_arg is not None
    return SlackWebhookNotifier(channel_arg, gateway)


def _write_summary(summary: RunSummary, stdout: TextIO) -> None:
    stdout.write(
        f"Checked {summary.pedigrees_checked} pedigree(s); "
        f"{summary.changes_detected} change(s) detected.\n",
    )


class _NullNotifier:
    def notify(self, notification: object) -> None:
        del notification


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
