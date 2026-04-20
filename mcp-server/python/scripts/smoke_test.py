"""Live smoke test: spawn evagene-mcp and exercise the MCP protocol."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


async def main() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env_file = Path(__file__).resolve().parents[3] / ".env"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "evagene_mcp"],
        env={k: v for k, v in os.environ.items() if k.startswith("EVAGENE_") or k in ("PATH",)},
    )

    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()
        print(f"initialized: server={init.serverInfo.name}", file=sys.stderr)

        tools = await session.list_tools()
        print(f"tools: {[t.name for t in tools.tools]}", file=sys.stderr)

        call = await session.call_tool("list_pedigrees", {})
        for block in call.content:
            if getattr(block, "type", None) == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
