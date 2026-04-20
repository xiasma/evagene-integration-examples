"""MCP wiring: registers tools against the Evagene client and dispatches.

This module only knows about the MCP SDK and our :mod:`tool_handlers`
catalogue — it holds no HTTP or business logic of its own.  Keeping the
wiring this thin means the server can be tested by calling its handlers
directly without spinning up the stdio transport.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .evagene_client import ApiError
from .tool_handlers import TOOL_SPECS, EvageneClientProtocol, ToolArgumentError, handle_call

SERVER_NAME = "evagene"

_logger = logging.getLogger(__name__)


def build_server(client: EvageneClientProtocol) -> Server[Any, Any]:
    """Create an MCP :class:`Server` that routes tool calls to *client*."""
    server: Server[Any, Any] = Server(SERVER_NAME)

    # The MCP SDK decorators are untyped ``Any`` returns; these ``type: ignore``
    # are scoped to the two registration sites so strict mypy passes elsewhere.

    @server.list_tools()  # type: ignore[no-untyped-call, misc]
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for spec in TOOL_SPECS
        ]

    @server.call_tool()  # type: ignore[misc]
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        args = arguments or {}
        try:
            result = await handle_call(client, name, args)
        except ToolArgumentError as error:
            return _error(f"Invalid arguments: {error}")
        except ApiError as error:
            _logger.warning("Evagene API error for tool %s: %s", name, error)
            return _error(str(error))

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    # The two handlers above are registered with the server via decorators; the
    # names are retained only so IDEs can still hop to them.
    _ = (_list_tools, _call_tool)

    return server


def _error(message: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {message}")]
