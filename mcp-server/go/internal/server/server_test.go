package server

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/evagene"
	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/tools"
)

type silentLogger struct{}

func (silentLogger) Info(string) {}
func (silentLogger) Warn(string) {}

type stubClient struct{}

func (stubClient) ListPedigrees(_ context.Context) ([]evagene.JSONObject, error) {
	return []evagene.JSONObject{
		{"id": "p1", "display_name": "Fam"},
	}, nil
}
func (stubClient) GetPedigree(_ context.Context, _ string) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}
func (stubClient) DescribePedigree(_ context.Context, _ string) (string, error) { return "", nil }
func (stubClient) ListRiskModels(_ context.Context, _ string) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}
func (stubClient) CalculateRisk(_ context.Context, _ evagene.CalculateRiskArgs) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}
func (stubClient) CreateIndividual(_ context.Context, _ evagene.CreateIndividualArgs) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}
func (stubClient) AddIndividualToPedigree(_ context.Context, _ string, _ string) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}
func (stubClient) AddRelative(_ context.Context, _ evagene.AddRelativeArgs) (evagene.JSONObject, error) {
	return evagene.JSONObject{}, nil
}

func connect(t *testing.T) (*mcp.ClientSession, func()) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)

	clientT, serverT := mcp.NewInMemoryTransports()
	srv := Build(stubClient{}, silentLogger{})

	serverDone := make(chan error, 1)
	go func() { serverDone <- srv.Run(ctx, serverT) }()

	client := mcp.NewClient(&mcp.Implementation{Name: "test", Version: "0"}, nil)
	session, err := client.Connect(ctx, clientT, nil)
	if err != nil {
		cancel()
		t.Fatalf("Connect err = %v", err)
	}

	cleanup := func() {
		_ = session.Close()
		cancel()
		<-serverDone
	}
	return session, cleanup
}

func TestServer_ListTools_ExposesAllSpecs(t *testing.T) {
	session, cleanup := connect(t)
	defer cleanup()

	list, err := session.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListTools err = %v", err)
	}
	got := map[string]bool{}
	for _, tool := range list.Tools {
		got[tool.Name] = true
	}
	for _, name := range []string{
		"list_pedigrees", "get_pedigree", "describe_pedigree",
		"list_risk_models", "calculate_risk", "add_individual", "add_relative",
	} {
		if !got[name] {
			t.Errorf("missing tool: %s", name)
		}
	}
}

func TestServer_CallListPedigrees_RoundTripsJSON(t *testing.T) {
	session, cleanup := connect(t)
	defer cleanup()

	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{
		Name:      "list_pedigrees",
		Arguments: json.RawMessage("{}"),
	})
	if err != nil {
		t.Fatalf("CallTool err = %v", err)
	}
	if res.IsError {
		t.Fatalf("IsError = true")
	}
	if len(res.Content) == 0 {
		t.Fatalf("no content blocks")
	}
	text, ok := res.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("first content is %T", res.Content[0])
	}
	var parsed []map[string]any
	if err := json.Unmarshal([]byte(text.Text), &parsed); err != nil {
		t.Fatalf("decode text: %v", err)
	}
	if len(parsed) != 1 || parsed[0]["id"] != "p1" {
		t.Errorf("parsed = %+v", parsed)
	}
}

func TestServer_MetadataAdvertisesName(t *testing.T) {
	if Name != "evagene" {
		t.Errorf("Name = %q", Name)
	}
	if Version != "0.1.0" {
		t.Errorf("Version = %q", Version)
	}
}
