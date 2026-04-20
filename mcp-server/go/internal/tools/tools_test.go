package tools

import (
	"context"
	"testing"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/evagene"
)

const (
	testPedigreeID = "3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e"
	testProbandID  = "11111111-1111-1111-1111-111111111111"
)

// FakeClient is an in-memory ClientPort used by handler tests.
type FakeClient struct {
	ListPedigreesResult           []evagene.JSONObject
	GetPedigreeResult             evagene.JSONObject
	DescribePedigreeResult        string
	ListRiskModelsResult          evagene.JSONObject
	CalculateRiskResult           evagene.JSONObject
	CreateIndividualResult        evagene.JSONObject
	AddIndividualToPedigreeResult evagene.JSONObject
	AddRelativeResult             evagene.JSONObject

	Calls []Call
}

type Call struct {
	Name string
	Args map[string]any
}

func (f *FakeClient) ListPedigrees(_ context.Context) ([]evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "list_pedigrees"})
	return f.ListPedigreesResult, nil
}

func (f *FakeClient) GetPedigree(_ context.Context, id string) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "get_pedigree", Args: map[string]any{"pedigree_id": id}})
	return f.GetPedigreeResult, nil
}

func (f *FakeClient) DescribePedigree(_ context.Context, id string) (string, error) {
	f.Calls = append(f.Calls, Call{Name: "describe_pedigree", Args: map[string]any{"pedigree_id": id}})
	return f.DescribePedigreeResult, nil
}

func (f *FakeClient) ListRiskModels(_ context.Context, id string) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "list_risk_models", Args: map[string]any{"pedigree_id": id}})
	return f.ListRiskModelsResult, nil
}

func (f *FakeClient) CalculateRisk(_ context.Context, args evagene.CalculateRiskArgs) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "calculate_risk", Args: map[string]any{
		"pedigree_id":  args.PedigreeID,
		"model":        args.Model,
		"counselee_id": args.CounseleeID,
	}})
	return f.CalculateRiskResult, nil
}

func (f *FakeClient) CreateIndividual(_ context.Context, args evagene.CreateIndividualArgs) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "create_individual", Args: map[string]any{
		"display_name":   args.DisplayName,
		"biological_sex": args.BiologicalSex,
	}})
	return f.CreateIndividualResult, nil
}

func (f *FakeClient) AddIndividualToPedigree(_ context.Context, pedigreeID, individualID string) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "add_individual_to_pedigree", Args: map[string]any{
		"pedigree_id":   pedigreeID,
		"individual_id": individualID,
	}})
	return f.AddIndividualToPedigreeResult, nil
}

func (f *FakeClient) AddRelative(_ context.Context, args evagene.AddRelativeArgs) (evagene.JSONObject, error) {
	f.Calls = append(f.Calls, Call{Name: "add_relative", Args: map[string]any{
		"pedigree_id":    args.PedigreeID,
		"relative_of":    args.RelativeOf,
		"relative_type":  args.RelativeType,
		"display_name":   args.DisplayName,
		"biological_sex": args.BiologicalSex,
	}})
	return f.AddRelativeResult, nil
}

func TestSpecs_EveryToolHasObjectSchema(t *testing.T) {
	for _, spec := range Specs() {
		if spec.InputSchema["type"] != "object" {
			t.Errorf("%s: schema.type = %v, want object", spec.Name, spec.InputSchema["type"])
		}
		if _, ok := spec.InputSchema["properties"]; !ok {
			t.Errorf("%s: schema missing properties", spec.Name)
		}
	}
}

func TestSpecs_ExposesAllSevenTools(t *testing.T) {
	wanted := map[string]bool{
		"list_pedigrees":    false,
		"get_pedigree":      false,
		"describe_pedigree": false,
		"list_risk_models":  false,
		"calculate_risk":    false,
		"add_individual":    false,
		"add_relative":      false,
	}
	for _, spec := range Specs() {
		wanted[spec.Name] = true
	}
	for name, found := range wanted {
		if !found {
			t.Errorf("missing tool: %s", name)
		}
	}
}

func TestDispatch_ListPedigreesSummarisesItems(t *testing.T) {
	fake := &FakeClient{
		ListPedigreesResult: []evagene.JSONObject{
			{
				"id":               testPedigreeID,
				"display_name":     "BRCA family",
				"date_represented": "2024-06-01",
				"disease_ids":      []any{"d1"},
				"owner":            "user-1",
			},
		},
	}
	result, err := Dispatch(context.Background(), fake, "list_pedigrees", nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	list, ok := result.([]map[string]any)
	if !ok {
		t.Fatalf("result type = %T", result)
	}
	if len(list) != 1 {
		t.Fatalf("len = %d", len(list))
	}
	first := list[0]
	if first["id"] != testPedigreeID || first["display_name"] != "BRCA family" ||
		first["date_represented"] != "2024-06-01" {
		t.Errorf("first = %+v", first)
	}
	if _, has := first["owner"]; has {
		t.Errorf("summary leaked owner field: %+v", first)
	}
}

func TestDispatch_GetPedigreeForwardsID(t *testing.T) {
	fake := &FakeClient{GetPedigreeResult: evagene.JSONObject{"id": testPedigreeID}}

	_, err := Dispatch(context.Background(), fake, "get_pedigree", map[string]any{
		"pedigree_id": testPedigreeID,
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if fake.Calls[0].Name != "get_pedigree" ||
		fake.Calls[0].Args["pedigree_id"] != testPedigreeID {
		t.Errorf("call = %+v", fake.Calls[0])
	}
}

func TestDispatch_DescribePedigreeWrapsText(t *testing.T) {
	fake := &FakeClient{DescribePedigreeResult: "A two-generation family..."}

	result, err := Dispatch(context.Background(), fake, "describe_pedigree", map[string]any{
		"pedigree_id": testPedigreeID,
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	got := result.(map[string]any)
	if got["pedigree_id"] != testPedigreeID || got["description"] != "A two-generation family..." {
		t.Errorf("result = %+v", got)
	}
}

func TestDispatch_CalculateRiskPassesFields(t *testing.T) {
	fake := &FakeClient{CalculateRiskResult: evagene.JSONObject{"model": "NICE"}}

	_, err := Dispatch(context.Background(), fake, "calculate_risk", map[string]any{
		"pedigree_id":  testPedigreeID,
		"model":        "NICE",
		"counselee_id": testProbandID,
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	args := fake.Calls[0].Args
	if args["pedigree_id"] != testPedigreeID || args["model"] != "NICE" ||
		args["counselee_id"] != testProbandID {
		t.Errorf("args = %+v", args)
	}
}

func TestDispatch_CalculateRiskRequiresModel(t *testing.T) {
	fake := &FakeClient{}
	_, err := Dispatch(context.Background(), fake, "calculate_risk", map[string]any{
		"pedigree_id": testPedigreeID,
	})
	if err == nil || !IsArgumentError(err) {
		t.Errorf("err = %v", err)
	}
}

func TestDispatch_AddIndividualCreatesAndAttaches(t *testing.T) {
	fake := &FakeClient{
		CreateIndividualResult: evagene.JSONObject{"id": testProbandID, "display_name": "Proband"},
	}

	result, err := Dispatch(context.Background(), fake, "add_individual", map[string]any{
		"pedigree_id":    testPedigreeID,
		"display_name":   "Proband",
		"biological_sex": "female",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	got := result.(map[string]any)
	if got["pedigree_id"] != testPedigreeID {
		t.Errorf("pedigree_id = %v", got["pedigree_id"])
	}
	ind := got["individual"].(evagene.JSONObject)
	if ind["id"] != testProbandID {
		t.Errorf("individual.id = %v", ind["id"])
	}
	names := []string{fake.Calls[0].Name, fake.Calls[1].Name}
	if names[0] != "create_individual" || names[1] != "add_individual_to_pedigree" {
		t.Errorf("call order = %v", names)
	}
}

func TestDispatch_AddRelativePassesKinship(t *testing.T) {
	fake := &FakeClient{AddRelativeResult: evagene.JSONObject{"individual": map[string]any{"id": "x"}}}

	_, err := Dispatch(context.Background(), fake, "add_relative", map[string]any{
		"pedigree_id":    testPedigreeID,
		"relative_of":    testProbandID,
		"relative_type":  "sister",
		"display_name":   "Jane",
		"biological_sex": "female",
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	args := fake.Calls[0].Args
	if args["relative_of"] != testProbandID || args["relative_type"] != "sister" ||
		args["display_name"] != "Jane" || args["biological_sex"] != "female" {
		t.Errorf("args = %+v", args)
	}
}

func TestDispatch_UnknownToolRaises(t *testing.T) {
	_, err := Dispatch(context.Background(), &FakeClient{}, "does_not_exist", nil)
	if err == nil || !IsArgumentError(err) {
		t.Errorf("err = %v", err)
	}
}

func TestDispatch_RequiresNonEmptyStringFields(t *testing.T) {
	fake := &FakeClient{}
	_, err := Dispatch(context.Background(), fake, "get_pedigree", map[string]any{
		"pedigree_id": "",
	})
	if err == nil || !IsArgumentError(err) {
		t.Errorf("err = %v", err)
	}
}
