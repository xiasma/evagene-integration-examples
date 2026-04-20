"""Pure helper to build the minted key's ``name`` field."""

from __future__ import annotations

_PEDIGREE_ID_PREFIX_LENGTH = 8


def build_key_name(pedigree_id: str, suffix: str) -> str:
    return f"share-{pedigree_id[:_PEDIGREE_ID_PREFIX_LENGTH]}-{suffix}"
