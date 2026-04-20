"""Test doubles for :class:`HttpGateway` and :class:`EvageneClient`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from evagene_mcp.http_gateway import HttpResponse


@dataclass
class StubResponse:
    status_code: int
    payload: Any = None
    text_body: str = ""

    def json(self) -> Any:
        return self.payload

    @property
    def text(self) -> str:
        return self.text_body


@dataclass
class RecordedCall:
    method: str
    url: str
    headers: dict[str, str]
    body: dict[str, Any] | None


ResponseFor = Callable[[str, str], StubResponse]


class RecordingGateway:
    """Fake :class:`HttpGateway` that records calls and returns scripted responses."""

    def __init__(self, response_for: ResponseFor) -> None:
        self._response_for = response_for
        self.calls: list[RecordedCall] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        self.calls.append(RecordedCall(method=method, url=url, headers=headers, body=body))
        return self._response_for(method, url)


@dataclass
class FakeClient:
    """In-memory stand-in for :class:`EvageneClient` used by tool-handler tests."""

    list_pedigrees_result: list[dict[str, Any]] = field(default_factory=list)
    get_pedigree_result: dict[str, Any] = field(default_factory=dict)
    describe_pedigree_result: str = ""
    list_risk_models_result: dict[str, Any] = field(default_factory=dict)
    calculate_risk_result: dict[str, Any] = field(default_factory=dict)
    create_individual_result: dict[str, Any] = field(default_factory=dict)
    add_individual_to_pedigree_result: dict[str, Any] = field(default_factory=dict)
    add_relative_result: dict[str, Any] = field(default_factory=dict)

    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def list_pedigrees(self) -> list[dict[str, Any]]:
        self.calls.append(("list_pedigrees", {}))
        return self.list_pedigrees_result

    async def get_pedigree(self, pedigree_id: str) -> dict[str, Any]:
        self.calls.append(("get_pedigree", {"pedigree_id": pedigree_id}))
        return self.get_pedigree_result

    async def describe_pedigree(self, pedigree_id: str) -> str:
        self.calls.append(("describe_pedigree", {"pedigree_id": pedigree_id}))
        return self.describe_pedigree_result

    async def list_risk_models(self, pedigree_id: str) -> dict[str, Any]:
        self.calls.append(("list_risk_models", {"pedigree_id": pedigree_id}))
        return self.list_risk_models_result

    async def calculate_risk(
        self,
        pedigree_id: str,
        *,
        model: str,
        counselee_id: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            ("calculate_risk", {
                "pedigree_id": pedigree_id, "model": model, "counselee_id": counselee_id,
            })
        )
        return self.calculate_risk_result

    async def create_individual(
        self, *, display_name: str, biological_sex: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("create_individual", {"display_name": display_name, "biological_sex": biological_sex})
        )
        return self.create_individual_result

    async def add_individual_to_pedigree(
        self, pedigree_id: str, individual_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("add_individual_to_pedigree", {
                "pedigree_id": pedigree_id, "individual_id": individual_id,
            })
        )
        return self.add_individual_to_pedigree_result

    async def add_relative(
        self,
        pedigree_id: str,
        *,
        relative_of: str,
        relative_type: str,
        display_name: str = "",
        biological_sex: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            ("add_relative", {
                "pedigree_id": pedigree_id,
                "relative_of": relative_of,
                "relative_type": relative_type,
                "display_name": display_name,
                "biological_sex": biological_sex,
            })
        )
        return self.add_relative_result


