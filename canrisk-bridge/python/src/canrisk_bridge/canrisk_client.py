"""Call Evagene's ``risk/canrisk`` endpoint and return the ``##CanRisk 2.0`` body."""

from __future__ import annotations

from .http_gateway import HttpGateway

CANRISK_HEADER = "##CanRisk 2.0"

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class CanRiskFormatError(ValueError):
    """Raised when the response body does not begin with the ``##CanRisk 2.0`` header."""


class CanRiskClient:
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

    def fetch(self, pedigree_id: str) -> str:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/risk/canrisk"
        response = self._http.get_text(url, headers=self._headers())
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(f"Evagene API returned HTTP {response.status_code} for {url}")

        body = response.text
        if not body.startswith(CANRISK_HEADER):
            raise CanRiskFormatError(
                f"Response body does not begin with {CANRISK_HEADER!r}; "
                f"check the pedigree ID and that your key has the 'analyze' scope."
            )
        return body

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Accept": "text/tab-separated-values",
        }
