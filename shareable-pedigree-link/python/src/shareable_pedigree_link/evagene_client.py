"""Call Evagene's API-keys and embed endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from .http_gateway import HttpGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class MintedKey:
    id: str
    plaintext_key: str


@dataclass(frozen=True)
class CreateApiKeyRequest:
    name: str
    rate_per_minute: int
    rate_per_day: int


class EvageneClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        http: HttpGateway,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def create_read_only_api_key(self, request: CreateApiKeyRequest) -> MintedKey:
        url = f"{self._base_url}/api/auth/me/api-keys"
        body: dict[str, Any] = {
            "name": request.name,
            "scopes": ["read"],
            "rate_limit_per_minute": request.rate_per_minute,
            "rate_limit_per_day": request.rate_per_day,
        }
        response = self._http.post_json(url, headers=self._headers(), body=body)
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(
                f"Evagene API returned HTTP {response.status_code} for {url}",
            )
        return _extract_minted_key(response.json(), url)

    def build_embed_url(self, pedigree_id: str, api_key: str) -> str:
        return f"{self._base_url}/api/embed/{pedigree_id}?api_key={quote(api_key, safe='')}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _extract_minted_key(payload: Any, url: str) -> MintedKey:
    if not isinstance(payload, dict):
        raise ApiError(f"Evagene API returned non-object JSON from {url}")
    plaintext_key = payload.get("key")
    api_key = payload.get("api_key")
    if not isinstance(plaintext_key, str) or not plaintext_key:
        raise ApiError(f"Evagene API response missing 'key' field from {url}")
    if not isinstance(api_key, dict):
        raise ApiError(f"Evagene API response missing 'api_key' object from {url}")
    key_id = api_key.get("id")
    if not isinstance(key_id, str) or not key_id:
        raise ApiError(f"Evagene API response missing 'api_key.id' from {url}")
    return MintedKey(id=key_id, plaintext_key=plaintext_key)
