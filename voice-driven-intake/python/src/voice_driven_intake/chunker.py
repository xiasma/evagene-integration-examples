"""Pure chunk-planning over a recorded audio track.

Given the total duration, the ``(start_ms, end_ms)`` ranges of silences
longer than the configured threshold, and a target maximum chunk size
in milliseconds, return a list of :class:`ChunkRange` covering the
whole recording without gaps.

No audio library is imported here on purpose: the function is exercised
in unit tests with hand-crafted silence lists.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkRange:
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def plan_chunks(
    *,
    duration_ms: int,
    silences_ms: list[tuple[int, int]],
    max_chunk_ms: int,
) -> list[ChunkRange]:
    """Split ``[0, duration_ms]`` at silence midpoints, keeping chunks under ``max_chunk_ms``.

    A single chunk is returned when the whole recording already fits under
    ``max_chunk_ms``. Otherwise we walk forward, splitting at the latest
    silence that still keeps the current chunk under the limit. If no silence
    is available before the limit, we hard-cut at the limit itself rather than
    emit a chunk that will fail upload.
    """
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    if max_chunk_ms <= 0:
        raise ValueError("max_chunk_ms must be positive")

    if duration_ms <= max_chunk_ms:
        return [ChunkRange(0, duration_ms)]

    midpoints = sorted(_midpoint(silence) for silence in silences_ms)
    chunks: list[ChunkRange] = []
    cursor = 0
    while cursor < duration_ms:
        limit = min(cursor + max_chunk_ms, duration_ms)
        if limit == duration_ms:
            chunks.append(ChunkRange(cursor, duration_ms))
            break
        boundary = _latest_boundary_within(midpoints, cursor, limit)
        chunks.append(ChunkRange(cursor, boundary))
        cursor = boundary
    return chunks


def _midpoint(silence: tuple[int, int]) -> int:
    start, end = silence
    if end < start:
        raise ValueError(f"Silence end ({end}) is before start ({start}).")
    return (start + end) // 2


def _latest_boundary_within(midpoints: list[int], cursor: int, limit: int) -> int:
    candidate = limit
    for point in midpoints:
        if cursor < point < limit:
            candidate = point
    return candidate
