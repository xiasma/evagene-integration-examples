// Package tools defines the seven MCP tool handlers exposed by the
// Evagene server.
//
// Each tool is a [Spec] — name, description, raw JSON Schema for the
// inputs, and a [Handler] that maps (client + args) onto a JSON-ready
// result.  The handlers depend on a narrow [ClientPort] interface so
// the tests can inject a fake client.
package tools

import (
	"context"
	"errors"
	"fmt"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/evagene"
)

// ClientPort is the subset of [evagene.Client] the handlers need.
type ClientPort interface {
	ListPedigrees(ctx context.Context) ([]evagene.JSONObject, error)
	GetPedigree(ctx context.Context, pedigreeID string) (evagene.JSONObject, error)
	DescribePedigree(ctx context.Context, pedigreeID string) (string, error)
	ListRiskModels(ctx context.Context, pedigreeID string) (evagene.JSONObject, error)
	CalculateRisk(ctx context.Context, args evagene.CalculateRiskArgs) (evagene.JSONObject, error)
	CreateIndividual(ctx context.Context, args evagene.CreateIndividualArgs) (evagene.JSONObject, error)
	AddIndividualToPedigree(ctx context.Context, pedigreeID, individualID string) (evagene.JSONObject, error)
	AddRelative(ctx context.Context, args evagene.AddRelativeArgs) (evagene.JSONObject, error)
}

// Handler is the shape every tool implements.
type Handler func(ctx context.Context, client ClientPort, args map[string]any) (any, error)

// Spec is an MCP tool declaration plus its handler.
type Spec struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     Handler
}

// ArgumentError is returned when a tool is called with missing or
// malformed arguments.
type ArgumentError struct {
	Msg string
}

func (e *ArgumentError) Error() string { return e.Msg }

// IsArgumentError reports whether err is an ArgumentError.
func IsArgumentError(err error) bool {
	var ae *ArgumentError
	return errors.As(err, &ae)
}

func newArgError(format string, args ...any) error {
	return &ArgumentError{Msg: fmt.Sprintf(format, args...)}
}

// ------------------------------------------------------------------
// Handlers
// ------------------------------------------------------------------

func listPedigrees(ctx context.Context, client ClientPort, _ map[string]any) (any, error) {
	pedigrees, err := client.ListPedigrees(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]map[string]any, 0, len(pedigrees))
	for _, p := range pedigrees {
		out = append(out, summarisePedigree(p))
	}
	return out, nil
}

func getPedigree(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	id, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	return client.GetPedigree(ctx, id)
}

func describePedigree(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	id, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	text, err := client.DescribePedigree(ctx, id)
	if err != nil {
		return nil, err
	}
	return map[string]any{"pedigree_id": id, "description": text}, nil
}

func listRiskModels(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	id, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	return client.ListRiskModels(ctx, id)
}

func calculateRisk(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	id, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	model, err := requireString(args, "model")
	if err != nil {
		return nil, err
	}
	counselee, err := optionalString(args, "counselee_id")
	if err != nil {
		return nil, err
	}
	return client.CalculateRisk(ctx, evagene.CalculateRiskArgs{
		PedigreeID:  id,
		Model:       model,
		CounseleeID: counselee,
	})
}

func addIndividual(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	pedigreeID, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	displayName, err := requireString(args, "display_name")
	if err != nil {
		return nil, err
	}
	sex, err := requireString(args, "biological_sex")
	if err != nil {
		return nil, err
	}

	individual, err := client.CreateIndividual(ctx, evagene.CreateIndividualArgs{
		DisplayName:   displayName,
		BiologicalSex: sex,
	})
	if err != nil {
		return nil, err
	}
	individualID, err := requireString(individual, "id")
	if err != nil {
		return nil, err
	}
	if _, err := client.AddIndividualToPedigree(ctx, pedigreeID, individualID); err != nil {
		return nil, err
	}
	return map[string]any{"pedigree_id": pedigreeID, "individual": individual}, nil
}

func addRelative(ctx context.Context, client ClientPort, args map[string]any) (any, error) {
	pedigreeID, err := requireString(args, "pedigree_id")
	if err != nil {
		return nil, err
	}
	relativeOf, err := requireString(args, "relative_of")
	if err != nil {
		return nil, err
	}
	relativeType, err := requireString(args, "relative_type")
	if err != nil {
		return nil, err
	}
	displayName, err := optionalString(args, "display_name")
	if err != nil {
		return nil, err
	}
	biologicalSex, err := optionalString(args, "biological_sex")
	if err != nil {
		return nil, err
	}
	return client.AddRelative(ctx, evagene.AddRelativeArgs{
		PedigreeID:    pedigreeID,
		RelativeOf:    relativeOf,
		RelativeType:  relativeType,
		DisplayName:   displayName,
		BiologicalSex: biologicalSex,
	})
}

// ------------------------------------------------------------------
// Catalogue
// ------------------------------------------------------------------

var pedigreeIDSchema = map[string]any{
	"type":        "string",
	"description": "UUID of the pedigree.",
}

var biologicalSexSchema = map[string]any{
	"type":        "string",
	"enum":        []any{"male", "female", "unknown"},
	"description": "Biological sex of the individual.",
}

// Specs returns the fixed catalogue of tools the server exposes.
//
// Returning a fresh slice on each call prevents callers from mutating a
// package-level global.
func Specs() []Spec {
	return []Spec{
		{
			Name:        "list_pedigrees",
			Description: "List all pedigrees owned by the authenticated user.",
			InputSchema: map[string]any{
				"type":                 "object",
				"properties":           map[string]any{},
				"additionalProperties": false,
			},
			Handler: listPedigrees,
		},
		{
			Name:        "get_pedigree",
			Description: "Fetch the full pedigree detail — individuals, relationships, eggs, diseases.",
			InputSchema: map[string]any{
				"type":                 "object",
				"properties":           map[string]any{"pedigree_id": pedigreeIDSchema},
				"required":             []any{"pedigree_id"},
				"additionalProperties": false,
			},
			Handler: getPedigree,
		},
		{
			Name:        "describe_pedigree",
			Description: "Generate a structured English description of the pedigree, suitable for clinical reasoning.",
			InputSchema: map[string]any{
				"type":                 "object",
				"properties":           map[string]any{"pedigree_id": pedigreeIDSchema},
				"required":             []any{"pedigree_id"},
				"additionalProperties": false,
			},
			Handler: describePedigree,
		},
		{
			Name:        "list_risk_models",
			Description: "List the risk models available for this pedigree (e.g. NICE, TYRER_CUZICK, BRCAPRO).",
			InputSchema: map[string]any{
				"type":                 "object",
				"properties":           map[string]any{"pedigree_id": pedigreeIDSchema},
				"required":             []any{"pedigree_id"},
				"additionalProperties": false,
			},
			Handler: listRiskModels,
		},
		{
			Name:        "calculate_risk",
			Description: "Run a named risk model against the pedigree and return the structured result.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"pedigree_id": pedigreeIDSchema,
					"model": map[string]any{
						"type":        "string",
						"description": "Risk-model enum, e.g. NICE, TYRER_CUZICK, CLAUS, BRCAPRO, AUTOSOMAL_DOMINANT.",
					},
					"counselee_id": map[string]any{
						"type":        "string",
						"description": "Optional UUID of the target individual; defaults to the proband.",
					},
				},
				"required":             []any{"pedigree_id", "model"},
				"additionalProperties": false,
			},
			Handler: calculateRisk,
		},
		{
			Name:        "add_individual",
			Description: "Create a new individual and attach them to the pedigree. Returns the stored individual.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"pedigree_id":    pedigreeIDSchema,
					"display_name":   map[string]any{"type": "string", "description": "Human-readable name."},
					"biological_sex": biologicalSexSchema,
				},
				"required":             []any{"pedigree_id", "display_name", "biological_sex"},
				"additionalProperties": false,
			},
			Handler: addIndividual,
		},
		{
			Name:        "add_relative",
			Description: "Add a new individual related to an existing one by kinship type (father, sister, cousin, etc.).",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"pedigree_id": pedigreeIDSchema,
					"relative_of": map[string]any{
						"type":        "string",
						"description": "UUID of the existing individual whose relative is being added.",
					},
					"relative_type": map[string]any{
						"type": "string",
						"description": "Kinship enum: father, mother, son, daughter, brother, sister, " +
							"half_brother, half_sister, paternal_grandfather, paternal_grandmother, " +
							"maternal_grandfather, maternal_grandmother, grandson, granddaughter, " +
							"paternal_uncle, paternal_aunt, maternal_uncle, maternal_aunt, " +
							"nephew, niece, first_cousin, partner, step_father, step_mother, unrelated.",
					},
					"display_name": map[string]any{
						"type":        "string",
						"description": "Optional human-readable name for the new individual.",
					},
					"biological_sex": biologicalSexSchema,
				},
				"required":             []any{"pedigree_id", "relative_of", "relative_type"},
				"additionalProperties": false,
			},
			Handler: addRelative,
		},
	}
}

// Dispatch finds the tool by name and runs it with the supplied args.
func Dispatch(ctx context.Context, client ClientPort, name string, args map[string]any) (any, error) {
	for _, spec := range Specs() {
		if spec.Name == name {
			if args == nil {
				args = map[string]any{}
			}
			return spec.Handler(ctx, client, args)
		}
	}
	return nil, newArgError("unknown tool: %s", name)
}

// ------------------------------------------------------------------
// Argument helpers
// ------------------------------------------------------------------

func requireString(src map[string]any, key string) (string, error) {
	raw, ok := src[key]
	if !ok {
		return "", newArgError("missing string field: %q", key)
	}
	s, ok := raw.(string)
	if !ok || s == "" {
		return "", newArgError("missing or empty string field: %q", key)
	}
	return s, nil
}

func optionalString(src map[string]any, key string) (string, error) {
	raw, ok := src[key]
	if !ok || raw == nil {
		return "", nil
	}
	s, ok := raw.(string)
	if !ok {
		return "", newArgError("field %q must be a string when provided", key)
	}
	return s, nil
}

func summarisePedigree(item evagene.JSONObject) map[string]any {
	diseaseIDs, _ := item["disease_ids"].([]any)
	if diseaseIDs == nil {
		diseaseIDs = []any{}
	}
	return map[string]any{
		"id":               item["id"],
		"display_name":     item["display_name"],
		"date_represented": item["date_represented"],
		"disease_ids":      diseaseIDs,
	}
}
