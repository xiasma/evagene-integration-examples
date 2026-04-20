"""Clock abstraction so timestamps are testable."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now_iso(self) -> str: ...

    def now_epoch_seconds(self) -> int: ...


class SystemClock:
    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def now_epoch_seconds(self) -> int:
        return int(time.time())
