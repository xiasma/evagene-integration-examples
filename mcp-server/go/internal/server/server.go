// Package server wires the tool catalogue onto an MCP SDK server.
//
// This is the only package that knows about the upstream
// github.com/modelcontextprotocol/go-sdk types.  Everything below it
// (config, httpgateway, evagene, tools) is SDK-free and trivially
// testable without the MCP machinery.
package server

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/evagene"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/tools"
)

// Name advertised to MCP clients.
const Name = "evagene"

// Version advertised to MCP clients.
const Version = "0.1.0"

// Logger is the subset of logger.Stream the server package uses.
type Logger interface {
	Info(message string)
	Warn(message string)
}

// Build returns a configured *mcp.Server that routes every tool call to
// client via tools.Dispatch.
//
// The server is not yet connected to a transport — the caller decides
// whether to run it over stdio (production) or an in-memory pair (tests).
func Build(client tools.ClientPort, log Logger) *mcp.Server {
	server := mcp.NewServer(&mcp.Implementation{Name: Name, Version: Version}, nil)

	for _, spec := range tools.Specs() {
		register(server, client, log, spec)
	}
	return server
}

func register(server *mcp.Server, client tools.ClientPort, log Logger, spec tools.Spec) {
	schemaJSON, err := json.Marshal(spec.InputSchema)
	if err != nil {
		// The schemas are constant and well-formed; a marshal failure
		// here is a programmer error, not a runtime condition.
		panic(fmt.Sprintf("tool %q: encode input schema: %v", spec.Name, err))
	}

	tool := &mcp.Tool{
		Name:        spec.Name,
		Description: spec.Description,
		InputSchema: json.RawMessage(schemaJSON),
	}

	handler := makeHandler(client, log, spec)
	server.AddTool(tool, handler)
}

func makeHandler(client tools.ClientPort, log Logger, spec tools.Spec) mcp.ToolHandler {
	return func(ctx context.Context, req *mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := map[string]any{}
		if len(req.Params.Arguments) > 0 {
			if err := json.Unmarshal(req.Params.Arguments, &args); err != nil {
				return errorResult(fmt.Sprintf("invalid arguments: %v", err)), nil
			}
		}

		result, err := spec.Handler(ctx, client, args)
		if err != nil {
			if tools.IsArgumentError(err) {
				return errorResult("Invalid arguments: " + err.Error()), nil
			}
			if evagene.IsApiError(err) {
				log.Warn(fmt.Sprintf("Evagene API error for tool %s: %s", spec.Name, err.Error()))
				return errorResult(err.Error()), nil
			}
			return nil, err
		}

		text, err := json.MarshalIndent(result, "", "  ")
		if err != nil {
			return nil, fmt.Errorf("encode %s result: %w", spec.Name, err)
		}
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{Text: string(text)}},
		}, nil
	}
}

func errorResult(message string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{&mcp.TextContent{Text: "Error: " + message}},
	}
}
