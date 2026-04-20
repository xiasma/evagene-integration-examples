// Package app is the composition root.
//
// It turns the process environment and stdio streams into a running MCP
// server, then blocks until the transport closes.  All moving parts are
// injected from main so the whole pipeline is testable end-to-end.
package app

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/config"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/evagene"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/httpgateway"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/logger"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/server"
)

// ExitUsage is the sysexits.h "command-line usage error" code.
const ExitUsage = 64

// httpTimeout is applied to every outbound request to the Evagene API.
const httpTimeout = 30 * time.Second

// Run is the composition root.  It returns an exit code; callers are
// responsible for passing it to os.Exit.
//
// stderr is the only writable stream — stdout is reserved for the MCP
// transport.
func Run(ctx context.Context, env config.Lookup, stderr io.Writer) int {
	cfg, err := config.Load(env)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "evagene-mcp: %s\n", err.Error())
		return ExitUsage
	}

	log := logger.New(stderr)
	client := evagene.NewClient(cfg.BaseURL, cfg.APIKey, httpgateway.NewNetHTTP(httpTimeout))
	srv := server.Build(client, log)

	log.Info(fmt.Sprintf("evagene-mcp starting (baseUrl=%s)", cfg.BaseURL))

	transport := &mcp.StdioTransport{}
	if err := srv.Run(ctx, transport); err != nil && !errors.Is(err, context.Canceled) {
		log.Error(err.Error())
		return 1
	}
	return 0
}

// LookupFromOS adapts os.LookupEnv to config.Lookup.
func LookupFromOS() config.Lookup { return os.LookupEnv }
