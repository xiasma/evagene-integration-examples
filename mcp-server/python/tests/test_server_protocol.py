"""Smoke test: real MCP client talks to our server over an in-memory transport."""

from __future__ import annotations

import json
from typing import Any, cast

from mcp.shared.memory import create_connected_server_and_client_session

from evagene_mcp.evagene_client import EvageneClient
from evagene_mcp.server import build_server

from .fakes import RecordingGateway, StubResponse


def _client_with(gateway: RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


async def test_list_tools_exposes_every_spec() -> None:
    gateway = RecordingGateway(lambda _m, _u: StubResponse(200, []))
    server = build_server(_client_with(gateway))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.list_tools()

    names = {tool.name for tool in result.tools}
    assert {
        "list_pedigrees",
        "get_pedigree",
        "describe_pedigree",
        "list_risk_models",
        "calculate_risk",
        "add_individual",
        "add_relative",
    }.issubset(names)


async def test_call_list_pedigrees_round_trips_json() -> None:
    payload: list[dict[str, Any]] = [{"id": "p1", "display_name": "Fam"}]
    gateway = RecordingGateway(lambda _m, _u: StubResponse(200, payload))
    server = build_server(_client_with(gateway))

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool("list_pedigrees", {})

    assert not result.isError
    text_block = cast(Any, result.content[0])
    assert text_block.type == "text"
    parsed = json.loads(text_block.text)
    assert parsed == [
        {"id": "p1", "display_name": "Fam", "date_represented": None, "disease_ids": []}
    ]
