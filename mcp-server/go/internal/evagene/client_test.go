package evagene

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/httpgateway"
)

const (
	pedigreeID  = "3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e"
	counseleeID = "11111111-1111-1111-1111-111111111111"
	testBase    = "https://evagene.example"
)

func loadFixture(t *testing.T, name string) []byte {
	t.Helper()
	// go/internal/evagene -> ../../.. -> mcp-server/, fixtures/<name>
	root, err := filepath.Abs(filepath.Join("..", "..", "..", "fixtures", name))
	if err != nil {
		t.Fatalf("filepath.Abs: %v", err)
	}
	b, err := os.ReadFile(root)
	if err != nil {
		t.Fatalf("read fixture %s: %v", name, err)
	}
	return b
}

func newFake(body []byte, status int) *httpgateway.Fake {
	return &httpgateway.Fake{Response: httpgateway.Response{StatusCode: status, Body: body}}
}

func TestClient_ListPedigrees(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-list-pedigrees.json"), 200)
	c := NewClient(testBase, "evg_test", gw)

	result, err := c.ListPedigrees(context.Background())
	if err != nil {
		t.Fatalf("ListPedigrees err = %v", err)
	}
	if len(result) != 2 {
		t.Errorf("len = %d, want 2", len(result))
	}

	call := gw.Calls[0]
	if call.Method != "GET" {
		t.Errorf("method = %s", call.Method)
	}
	if call.URL != testBase+"/api/pedigrees" {
		t.Errorf("url = %s", call.URL)
	}
	if call.Headers["X-API-Key"] != "evg_test" {
		t.Errorf("header = %q", call.Headers["X-API-Key"])
	}
}

func TestClient_GetPedigree(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-pedigree-detail.json"), 200)
	c := NewClient(testBase, "evg_test", gw)

	if _, err := c.GetPedigree(context.Background(), pedigreeID); err != nil {
		t.Fatalf("GetPedigree err = %v", err)
	}
	if got := gw.Calls[0].URL; got != testBase+"/api/pedigrees/"+pedigreeID {
		t.Errorf("url = %s", got)
	}
}

func TestClient_DescribePedigree_ReturnsText(t *testing.T) {
	gw := newFake([]byte("A two-generation family..."), 200)
	c := NewClient(testBase, "evg_test", gw)

	text, err := c.DescribePedigree(context.Background(), pedigreeID)
	if err != nil {
		t.Fatalf("DescribePedigree err = %v", err)
	}
	if text != "A two-generation family..." {
		t.Errorf("text = %q", text)
	}
	wantURL := testBase + "/api/pedigrees/" + pedigreeID + "/describe"
	if got := gw.Calls[0].URL; got != wantURL {
		t.Errorf("url = %s, want %s", got, wantURL)
	}
}

func TestClient_CalculateRisk_SendsModelAndCounselee(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-risk-nice.json"), 200)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.CalculateRisk(context.Background(), CalculateRiskArgs{
		PedigreeID:  pedigreeID,
		Model:       "NICE",
		CounseleeID: counseleeID,
	})
	if err != nil {
		t.Fatalf("CalculateRisk err = %v", err)
	}

	call := gw.Calls[0]
	if call.Method != "POST" {
		t.Errorf("method = %s", call.Method)
	}
	wantURL := testBase + "/api/pedigrees/" + pedigreeID + "/risk/calculate"
	if call.URL != wantURL {
		t.Errorf("url = %s", call.URL)
	}
	var body map[string]string
	if err := json.Unmarshal(call.Body, &body); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if body["model"] != "NICE" || body["counselee_id"] != counseleeID {
		t.Errorf("body = %+v", body)
	}
}

func TestClient_CalculateRisk_OmitsCounselee(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-risk-nice.json"), 200)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.CalculateRisk(context.Background(), CalculateRiskArgs{
		PedigreeID: pedigreeID,
		Model:      "NICE",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	var body map[string]any
	if err := json.Unmarshal(gw.Calls[0].Body, &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if _, has := body["counselee_id"]; has {
		t.Errorf("counselee_id unexpectedly present: %+v", body)
	}
	if body["model"] != "NICE" {
		t.Errorf("model = %v", body["model"])
	}
}

func TestClient_ListRiskModels(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-risk-models.json"), 200)
	c := NewClient(testBase, "evg_test", gw)

	result, err := c.ListRiskModels(context.Background(), pedigreeID)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if _, has := result["models"]; !has {
		t.Errorf("result missing models key: %+v", result)
	}
	wantURL := testBase + "/api/pedigrees/" + pedigreeID + "/risk/models"
	if got := gw.Calls[0].URL; got != wantURL {
		t.Errorf("url = %s", got)
	}
}

func TestClient_AddRelative(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-add-relative.json"), 201)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.AddRelative(context.Background(), AddRelativeArgs{
		PedigreeID:    pedigreeID,
		RelativeOf:    counseleeID,
		RelativeType:  "sister",
		DisplayName:   "Jane",
		BiologicalSex: "female",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	call := gw.Calls[0]
	wantURL := testBase + "/api/pedigrees/" + pedigreeID + "/register/add-relative"
	if call.URL != wantURL {
		t.Errorf("url = %s", call.URL)
	}
	var body map[string]any
	if err := json.Unmarshal(call.Body, &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["relative_of"] != counseleeID ||
		body["relative_type"] != "sister" ||
		body["display_name"] != "Jane" ||
		body["biological_sex"] != "female" {
		t.Errorf("body = %+v", body)
	}
}

func TestClient_AddRelative_OmitsBiologicalSexWhenEmpty(t *testing.T) {
	gw := newFake(loadFixture(t, "sample-add-relative.json"), 201)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.AddRelative(context.Background(), AddRelativeArgs{
		PedigreeID:   pedigreeID,
		RelativeOf:   counseleeID,
		RelativeType: "sister",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	var body map[string]any
	if err := json.Unmarshal(gw.Calls[0].Body, &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if _, has := body["biological_sex"]; has {
		t.Errorf("biological_sex unexpectedly present: %+v", body)
	}
}

func TestClient_RaisesApiError_OnNon2xx(t *testing.T) {
	gw := newFake([]byte(`{}`), 500)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.ListPedigrees(context.Background())
	if err == nil {
		t.Fatalf("expected error, got nil")
	}
	if !IsApiError(err) {
		t.Errorf("err is not ApiError: %v", err)
	}
}

func TestClient_AddIndividualToPedigree_UsesNestedURL(t *testing.T) {
	gw := newFake([]byte(`{"id":"x"}`), 200)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.AddIndividualToPedigree(context.Background(), pedigreeID, "ind-1")
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	wantURL := testBase + "/api/pedigrees/" + pedigreeID + "/individuals/ind-1"
	if got := gw.Calls[0].URL; got != wantURL {
		t.Errorf("url = %s", got)
	}
}

func TestClient_CreateIndividual_PostsPayload(t *testing.T) {
	gw := newFake([]byte(`{"id":"x"}`), 200)
	c := NewClient(testBase, "evg_test", gw)

	_, err := c.CreateIndividual(context.Background(), CreateIndividualArgs{
		DisplayName:   "Proband",
		BiologicalSex: "female",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	var body map[string]any
	if err := json.Unmarshal(gw.Calls[0].Body, &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["display_name"] != "Proband" || body["biological_sex"] != "female" {
		t.Errorf("body = %+v", body)
	}
}
