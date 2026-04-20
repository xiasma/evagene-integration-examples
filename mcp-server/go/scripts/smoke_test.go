//go:build smoke

// Command smoke_test connects to a freshly-spawned evagene-mcp binary
// over stdio and exercises the MCP protocol: initialize, tools/list,
// and tools/call for list_pedigrees.  It prints the server's reply to
// stdout so you can eyeball the pedigree list.
//
// Build and run with:
//
//	go build -o bin/evagene-mcp ./cmd/evagene-mcp
//	go run -tags smoke ./scripts
//
// The .env at the repo root is loaded for EVAGENE_API_KEY /
// EVAGENE_BASE_URL; host PATH is inherited.
package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "smoke test failed: %v\n", err)
		os.Exit(1)
	}
}

func run() error {
	env, err := loadEnv()
	if err != nil {
		return err
	}

	binary, err := filepath.Abs(filepath.Join("bin", binaryName()))
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, binary)
	cmd.Env = append(os.Environ(),
		"EVAGENE_API_KEY="+env["EVAGENE_API_KEY"],
		"EVAGENE_BASE_URL="+envOr(env, "EVAGENE_BASE_URL", "https://evagene.net"),
	)
	cmd.Stderr = os.Stderr

	transport := &mcp.CommandTransport{Command: cmd}
	client := mcp.NewClient(&mcp.Implementation{Name: "evagene-mcp-smoke", Version: "0.1.0"}, nil)

	session, err := client.Connect(ctx, transport, nil)
	if err != nil {
		return fmt.Errorf("connect: %w", err)
	}
	defer session.Close()

	fmt.Fprintf(os.Stderr, "initialized: %s\n", session.InitializeResult().ServerInfo.Name)

	list, err := session.ListTools(ctx, nil)
	if err != nil {
		return fmt.Errorf("list tools: %w", err)
	}
	names := make([]string, 0, len(list.Tools))
	for _, t := range list.Tools {
		names = append(names, t.Name)
	}
	fmt.Fprintf(os.Stderr, "tools: %s\n", strings.Join(names, ", "))

	call, err := session.CallTool(ctx, &mcp.CallToolParams{Name: "list_pedigrees"})
	if err != nil {
		return fmt.Errorf("call list_pedigrees: %w", err)
	}
	for _, block := range call.Content {
		if text, ok := block.(*mcp.TextContent); ok {
			fmt.Println(text.Text)
		}
	}
	return nil
}

func loadEnv() (map[string]string, error) {
	root, err := filepath.Abs(filepath.Join("..", "..", ".env"))
	if err != nil {
		return nil, err
	}
	file, err := os.Open(root)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", root, err)
	}
	defer file.Close()

	env := map[string]string{}
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		eq := strings.Index(line, "=")
		if eq <= 0 {
			continue
		}
		env[strings.TrimSpace(line[:eq])] = strings.TrimSpace(line[eq+1:])
	}
	return env, scanner.Err()
}

func envOr(env map[string]string, key, fallback string) string {
	if v, ok := env[key]; ok && v != "" {
		return v
	}
	return fallback
}

func binaryName() string {
	if os.Getenv("GOOS") == "windows" || strings.Contains(strings.ToLower(os.Getenv("OS")), "windows") {
		return "evagene-mcp.exe"
	}
	return "evagene-mcp"
}
