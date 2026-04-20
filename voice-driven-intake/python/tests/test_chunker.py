from itertools import pairwise

import pytest

from voice_driven_intake.chunker import ChunkRange, plan_chunks


def test_short_audio_returns_single_chunk() -> None:
    chunks = plan_chunks(duration_ms=5000, silences_ms=[], max_chunk_ms=10_000)

    assert chunks == [ChunkRange(0, 5000)]


def test_single_silence_splits_at_midpoint() -> None:
    chunks = plan_chunks(
        duration_ms=20_000,
        silences_ms=[(8000, 10_000)],
        max_chunk_ms=12_000,
    )

    # Silence midpoint is 9000; that fits inside the 12000 limit for the first chunk.
    assert chunks == [ChunkRange(0, 9000), ChunkRange(9000, 20_000)]


def test_chunks_never_exceed_the_size_limit() -> None:
    chunks = plan_chunks(
        duration_ms=60_000,
        silences_ms=[(9500, 10_500), (19_500, 20_500), (29_500, 30_500)],
        max_chunk_ms=15_000,
    )

    assert all(chunk.duration_ms <= 15_000 for chunk in chunks)
    assert chunks[0].start_ms == 0
    assert chunks[-1].end_ms == 60_000
    # Chunks are contiguous with no gaps.
    for earlier, later in pairwise(chunks):
        assert earlier.end_ms == later.start_ms


def test_no_silence_falls_back_to_hard_cut() -> None:
    chunks = plan_chunks(duration_ms=25_000, silences_ms=[], max_chunk_ms=10_000)

    assert chunks == [
        ChunkRange(0, 10_000),
        ChunkRange(10_000, 20_000),
        ChunkRange(20_000, 25_000),
    ]


def test_silences_outside_first_window_are_ignored_for_first_cut() -> None:
    chunks = plan_chunks(
        duration_ms=30_000,
        silences_ms=[(28_000, 29_000)],
        max_chunk_ms=10_000,
    )

    # The silence midpoint (28500) is past the first window; first cut is at 10000.
    assert chunks[0] == ChunkRange(0, 10_000)


def test_invalid_duration_rejected() -> None:
    with pytest.raises(ValueError, match="duration_ms"):
        plan_chunks(duration_ms=0, silences_ms=[], max_chunk_ms=1000)


def test_invalid_max_chunk_rejected() -> None:
    with pytest.raises(ValueError, match="max_chunk_ms"):
        plan_chunks(duration_ms=1000, silences_ms=[], max_chunk_ms=0)
