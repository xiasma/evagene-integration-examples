# Evagene MCP server — Go

Go port of the Python / Node examples. Identical feature set: seven tools exposed over stdio so any MCP-aware AI assistant can list, inspect and mutate the pedigrees behind your [Evagene](https://evagene.net) account.

> **New to Evagene integrations?** Start with **[../../getting-started.md](../../getting-started.md)** before running the server.

See **[../README.md](../README.md)** for the cross-language overview, tool reference and caveats. This file only covers Go-specific setup.

## Prerequisites

- **Go 1.23 or newer.**
- An Evagene API key (see [../../getting-started.md](../../getting-started.md)).

## Environment variables

| Variable | Required | Default |
|---|---|---|
| `EVAGENE_API_KEY` | yes | — |
| `EVAGENE_BASE_URL` | no | `https://evagene.net` |

Copy `.env.example` to `.env` for local runs.

## Build and run

```sh
go build -o bin/evagene-mcp ./cmd/evagene-mcp

EVAGENE_API_KEY=evg_REPLACE_WITH_YOUR_KEY ./bin/evagene-mcp
```

The process blocks on stdin and writes MCP JSON-RPC frames to stdout. Kill with `Ctrl-C`.

## Claude Desktop config

```json
{
  "mcpServers": {
    "evagene": {
      "command": "/absolute/path/to/bin/evagene-mcp",
      "env": {
        "EVAGENE_API_KEY": "evg_REPLACE_WITH_YOUR_KEY",
        "EVAGENE_BASE_URL": "https://evagene.net"
      }
    }
  }
}
```

On Windows the binary is `evagene-mcp.exe`.

## Tests

```sh
go test ./...
```

Coverage, per package:

- `internal/config` — env parsing and validation errors.
- `internal/httpgateway` — `httptest`-driven concrete test plus a shared fake.
- `internal/evagene` — URL / body / headers per method, against the fake gateway.
- `internal/tools` — argument validation and passthrough via a fake `ClientPort`.
- `internal/server` — in-memory MCP transport smoke: `ListTools` + `CallTool` for `list_pedigrees`.
- `internal/app` — composition-root exit codes on missing config.
- `internal/logger` — deterministic output with an injected clock.

## Live smoke test

```sh
go build -o bin/evagene-mcp ./cmd/evagene-mcp
go run -tags smoke ./scripts
```

The smoke driver loads `../../.env`, spawns the compiled binary over `mcp.CommandTransport`, prints the server's reported tool list on stderr, and writes the `list_pedigrees` response to stdout.

## Project layout

```
cmd/evagene-mcp/       process entry; no business logic
internal/config/       env -> Config value object
internal/httpgateway/  HTTP abstraction + net/http adapter + in-process fake
internal/evagene/      thin REST client; one method per endpoint
internal/tools/        tool specs + handlers; depend on a narrow ClientPort
internal/server/       MCP SDK wiring — the only file that imports the SDK
internal/logger/       stderr-only structured logger
internal/app/          composition root; Run(ctx, env, stderr) -> exit code
scripts/smoke_test.go  live smoke driver (build tag: smoke)
```

All logs go to stderr. Stdout is the MCP transport — a stray write there corrupts JSON-RPC framing.

## SDK version

`github.com/modelcontextprotocol/go-sdk` is pinned in `go.mod`. If you bump the version, the only file that should need adjustment is `internal/server/server.go` — the rest of the codebase is SDK-agnostic and is exercised entirely by Go's standard `testing` package.

## Caveats

See [../README.md](../README.md) for the shared clinical / regulatory caveats. This is an example integration, not a validated clinical tool.
