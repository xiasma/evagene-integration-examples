"""Thin client for the Evagene endpoints used by the cascade-letters demo.

One method per endpoint; parses response JSON into small, frozen domain
objects (:class:`RegisterData`, :class:`Template`).  No orchestration here
— that lives in :mod:`cascade_service`.  Depends on an :class:`HttpGateway`
so tests can substitute a fake.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .http_gateway import HttpGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class RegisterRow:
    individual_id: str
    display_name: str
    relationship_to_proband: str


@dataclass(frozen=True)
class RegisterData:
    proband_id: str | None
    rows: tuple[RegisterRow, ...]


@dataclass(frozen=True)
class Template:
    id: str
    name: str


@dataclass(frozen=True)
class CreateTemplateArgs:
    name: str
    description: str
    user_prompt_template: str


class EvageneApi(Protocol):
    """Surface the service depends on; tests supply their own implementation."""

    def fetch_register(self, pedigree_id: str) -> RegisterData: ...

    def list_templates(self) -> list[Template]: ...

    def create_template(self, args: CreateTemplateArgs) -> Template: ...

    def run_template(self, template_id: str, pedigree_id: str) -> str: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def fetch_register(self, pedigree_id: str) -> RegisterData:
        payload = self._request("GET", f"/api/pedigrees/{pedigree_id}/register")
        proband_id = payload.get("proband_id")
        rows_raw = payload.get("rows", [])
        if not isinstance(rows_raw, list):
            raise EvageneApiError("Register response field 'rows' is not a list.")
        rows = tuple(_parse_register_row(item) for item in rows_raw)
        return RegisterData(
            proband_id=proband_id if isinstance(proband_id, str) else None,
            rows=rows,
        )

    def list_templates(self) -> list[Template]:
        payload = self._request("GET", "/api/templates")
        if not isinstance(payload, list):
            raise EvageneApiError("GET /api/templates did not return a JSON array.")
        return [_parse_template(item) for item in payload]

    def create_template(self, args: CreateTemplateArgs) -> Template:
        body = {
            "name": args.name,
            "description": args.description,
            "user_prompt_template": args.user_prompt_template,
            "is_public": False,
        }
        payload = self._request("POST", "/api/templates", body=body)
        return _parse_template(payload)

    def run_template(self, template_id: str, pedigree_id: str) -> str:
        # Server takes ``pedigree_id`` as a query parameter; no request body is accepted.
        path = f"/api/templates/{template_id}/run?pedigree_id={pedigree_id}"
        payload = self._request("POST", path, body={})
        text = payload.get("text")
        if not isinstance(text, str):
            raise EvageneApiError("Template run response is missing string field 'text'.")
        return text

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        verb: Any = method  # narrowed by the callers
        response = self._http.send(verb, url, headers=self._headers(), body=body)
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise EvageneApiError(
                f"Evagene API returned HTTP {response.status_code} for {method} {path}"
            )
        return response.json()

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _parse_register_row(raw: Any) -> RegisterRow:
    if not isinstance(raw, dict):
        raise EvageneApiError("Register row is not an object.")
    return RegisterRow(
        individual_id=_require_str(raw, "individual_id"),
        display_name=_optional_str(raw, "display_name"),
        relationship_to_proband=_optional_str(raw, "relationship_to_proband"),
    )


def _parse_template(raw: Any) -> Template:
    if not isinstance(raw, dict):
        raise EvageneApiError("Template payload is not an object.")
    return Template(
        id=_require_str(raw, "id"),
        name=_optional_str(raw, "name"),
    )


def _require_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise EvageneApiError(f"Response field {key!r} is missing or not a string.")
    return value


def _optional_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    return value if isinstance(value, str) else ""
