# Evagene MCP server

**Plug Evagene into any MCP-aware AI assistant.** Drop this server's stanza into your Claude Desktop, Cursor, or custom-agent config, give it your [Evagene](https://evagene.net) API key, and the agent can list your pedigrees, pull full family-history detail, describe a family in structured English, list available risk models, run a named risk model, and even add individuals or relatives — all over Anthropic's Model Context Protocol.

The result: an AI session that can reason over your actual pedigrees instead of dummy data, pulling and (with a `write`-scoped key) mutating family-history structure on demand.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Developers building AI assistants** that need first-class access to a user's pedigrees — Claude Desktop plugins, Cursor agents, bespoke LangChain / MCP clients.
- **Genetic counsellors piloting LLM-assisted workflows** who want their assistant to draft a family summary, pull up a risk number, or add a newly-identified relative without leaving the chat.
- **Clinical-AI researchers** prototyping agentic pedigree triage or multi-step family-history reasoning against a live API.

## What Evagene surface this uses

- **Model Context Protocol** — stdio transport, JSON-RPC, standard `initialize` / `tools/list` / `tools/call` surface.
- Each tool is a thin wrapper around the Evagene **REST API** at `https://evagene.net/api/*`.
- **Authentication** — `X-API-Key: evg_...`. Scopes: `read` is enough for the lookup tools; `write` is needed for `add_individual` / `add_relative`; `analyze` is needed for `calculate_risk`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

This demo is deliberately a **client-side / third-party** MCP server. The Evagene product itself also ships an MCP server, but that one speaks directly to the product's internal store. This one only uses the public REST API — exactly what any external integrator can build.

## Prerequisites

1. An Evagene account and API key with the scopes you want the agent to have. Start narrow: `read` only, then expand if the agent needs to mutate data. See [getting-started.md](../getting-started.md).
2. An MCP-capable client. Any of:
   - **Claude Desktop** — native support via `claude_desktop_config.json`.
   - **Cursor** — MCP settings panel.
   - Any custom client using the `@modelcontextprotocol/sdk` (Node) or `mcp` (Python) SDK.
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Every language reads the same two environment variables. Each language folder ships a `.env.example` you can copy to `.env` for local runs. When wired into a host application (Claude Desktop, Cursor), the host injects the env vars via its config stanza — no `.env` is involved.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## Wiring into Claude Desktop

Claude Desktop reads `claude_desktop_config.json` (location differs per OS — see Anthropic's docs). Add an `evagene` entry under `mcpServers`. The command + args depend on the language you installed.

**Python:**

```json
{
  "mcpServers": {
    "evagene": {
      "command": "python",
      "args": ["-m", "evagene_mcp"],
      "env": {
        "EVAGENE_API_KEY": "evg_REPLACE_WITH_YOUR_KEY",
        "EVAGENE_BASE_URL": "https://evagene.net"
      }
    }
  }
}
```

**Node:**

```json
{
  "mcpServers": {
    "evagene": {
      "command": "npx",
      "args": ["-y", "evagene-mcp-server"],
      "env": {
        "EVAGENE_API_KEY": "evg_REPLACE_WITH_YOUR_KEY",
        "EVAGENE_BASE_URL": "https://evagene.net"
      }
    }
  }
}
```

If you are running the Node version straight out of this repo rather than a published package, point `command` at `node` and `args` at the built `dist/main.js` (or at `tsx` + `src/main.ts` during development).

**Go:**

```json
{
  "mcpServers": {
    "evagene": {
      "command": "/absolute/path/to/mcp-server/go/bin/evagene-mcp",
      "env": {
        "EVAGENE_API_KEY": "evg_REPLACE_WITH_YOUR_KEY",
        "EVAGENE_BASE_URL": "https://evagene.net"
      }
    }
  }
}
```

The Go build produces a statically-linked single binary — no runtime required on the target machine. On Windows the binary is `evagene-mcp.exe`.

Restart the client after saving. The Evagene tools show up alongside any other MCP servers the client knows about.

## Run it

All three implementations expect `EVAGENE_API_KEY` in the environment, block on stdin, and write JSON-RPC frames to stdout. Kill with `Ctrl-C`. For day-to-day use you would wire these into a host (Claude Desktop, Cursor) rather than run them by hand — the commands below exist for local testing and packaging.

### Run it in Python 3.11+

```bash
cd python

# Create and activate a virtual environment
python -m venv .venv

# Windows (cmd / PowerShell):
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install the demo package + its dev tools (editable install so python -m <pkg> works)
pip install -e ".[dev]"

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the MCP server
python -m evagene_mcp
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in Node 20+

```bash
cd node

# Install dependencies
npm install

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the MCP server
npm start
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

### Run it in Go 1.23+

```bash
cd go

# Build the binary
go build -o bin/evagene-mcp ./cmd/evagene-mcp

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the MCP server
./bin/evagene-mcp
```

Run the tests (optional):

```bash
go test ./...
go vet ./...
```

## Tool reference

All tools use raw JSON Schema for their inputs — that schema *is* the documentation.

- **`list_pedigrees`** — `{}`. Returns `[{id, display_name, date_represented, disease_ids}]` for every pedigree you own.
- **`get_pedigree`** — `{pedigree_id: UUID}`. Full pedigree detail: every individual, relationship, egg, disease.
- **`describe_pedigree`** — `{pedigree_id: UUID}`. Structured English description built server-side — the same deterministic summary Evagene's own LLM features use as a prompt input. Returns `{pedigree_id, description}`.
- **`list_risk_models`** — `{pedigree_id: UUID}`. Which models this pedigree can actually run (some need specific diseases or structure).
- **`calculate_risk`** — `{pedigree_id: UUID, model: string, counselee_id?: UUID}`. `model` is the enum name: `NICE`, `TYRER_CUZICK`, `CLAUS`, `BRCAPRO`, `AUTOSOMAL_DOMINANT`, `MMRpro`, etc. `counselee_id` defaults to the pedigree's proband. Returns the full `RiskResult` from Evagene — keep the structure intact, the interesting fields differ per model.
- **`add_individual`** — `{pedigree_id, display_name, biological_sex}`. Creates a new individual and attaches them to the pedigree.
- **`add_relative`** — `{pedigree_id, relative_of, relative_type, display_name?, biological_sex?}`. `relative_type` is the Evagene kinship enum: `father`, `mother`, `sister`, `paternal_uncle`, `first_cousin`, `partner`, `step_father`, etc. (the register endpoint also exposes `relative-types` for discovery if you want to expose it as a tool).

Tool results are returned as JSON-encoded text content blocks, which every MCP client renders cleanly.

## Architecture (identical in both languages)

```
 EVAGENE_API_KEY  ──►  Config (value object, validated)
                                │
                                ▼
                          EvageneClient ◄── HttpGateway (abstraction)
                                │
                                ▼
                      tool handlers (pure functions, name + args → JSON)
                                │
                                ▼
                      MCP Server (list_tools / call_tool wiring)
                                │
                                ▼
                        stdio transport ◄── AI-agent host (Claude Desktop, Cursor, ...)
```

- **config** — immutable value object; reads `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.
- **http_gateway / HttpGateway** — one-method abstraction the tests fake.
- **evagene_client / EvageneClient** — one method per Evagene endpoint the tools need. No domain logic.
- **tool_handlers** — pure functions mapping `(name, args)` → JSON. Depend on a small `EvageneClientPort` interface so the tests use a fake client, not the real one.
- **server** — MCP SDK wiring: registers the tool list + schemas, dispatches calls.
- **app / main** — composition root; reads config, wires pieces, starts the stdio loop.

Every module has one responsibility; the reading order is identical in Python and Node.

## Logging

**All logs go to stderr.** `stdout` is the MCP transport — any stray `print` / `console.log` on stdout breaks the JSON-RPC framing. Both implementations wire their loggers to stderr in the composition root, and the test suites assert the protocol round-trips cleanly.

Set `EVAGENE_MCP_LOG_LEVEL=DEBUG` (Python) for more verbose output while debugging.

## Test fixtures

The canonical REST responses (`sample-list-pedigrees.json`, `sample-pedigree-detail.json`, `sample-risk-models.json`, `sample-risk-nice.json`, `sample-add-relative.json`) live at `fixtures/` and are loaded by both languages' client tests. Update them in one place when the wire contract moves.

## Caveats

- **The agent can do whatever your API key scopes allow.** An `analyze` key lets it run risk calculations; a `write` key lets it mutate pedigree data. Mint narrow keys, audit what the agent does, and do not run these tools unattended without oversight. Revoke a key at any time from the Evagene account settings.
- **Describe-pedigree summaries are deterministic, but still summaries.** They are designed for LLM prompt injection, not for clinical record-keeping. Use `get_pedigree` if you need the raw structure.
- **Risk models carry model-specific caveats.** Tyrer-Cuzick is an IBIS-style approximation; BOADICEA is not bundled (Evagene can export a `##CanRisk 2.0` file and you upload it at canrisk.org). NICE is a categorical triage, not a continuous risk.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
