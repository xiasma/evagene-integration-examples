// Command evagene-mcp runs the Evagene MCP server over stdio.
//
// It reads EVAGENE_API_KEY (required) and EVAGENE_BASE_URL (optional,
// defaults to https://evagene.net) from the environment, then blocks
// serving MCP requests until stdin closes or SIGINT/SIGTERM is received.
//
// All log output goes to stderr — stdout is the MCP transport.
package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/app"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	os.Exit(app.Run(ctx, app.LookupFromOS(), os.Stderr))
}
