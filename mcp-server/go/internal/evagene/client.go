// Package evagene is a thin client over the Evagene REST endpoints the
// MCP tools need.
//
// One method per endpoint.  Each method shapes the URL, delegates the
// transport to [httpgateway.Gateway], and returns [ApiError] on any
// non-2xx response.  No domain logic lives here — that belongs in the
// tool handlers.
package evagene

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/evagene/evagene-integration-examples/mcp-server/go/internal/httpgateway"
)

const (
	httpOKLower = 200
	httpOKUpper = 300
)

// ApiError is raised when the Evagene API is unreachable or returns a
// non-2xx response.
type ApiError struct {
	Msg string
}

func (e *ApiError) Error() string { return e.Msg }

func newApiError(format string, args ...any) error {
	return &ApiError{Msg: fmt.Sprintf(format, args...)}
}

// JSONObject is the untyped map shape returned by every endpoint.
type JSONObject = map[string]any

// Client wraps the Evagene REST API.
type Client struct {
	baseURL string
	apiKey  string
	http    httpgateway.Gateway
}

// NewClient returns a Client bound to the given base URL and API key.
func NewClient(baseURL, apiKey string, http httpgateway.Gateway) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		apiKey:  apiKey,
		http:    http,
	}
}

// ListPedigrees returns every pedigree the authenticated user owns.
func (c *Client) ListPedigrees(ctx context.Context) ([]JSONObject, error) {
	resp, err := c.do(ctx, "GET", "/api/pedigrees", nil)
	if err != nil {
		return nil, err
	}
	var out []JSONObject
	if err := json.Unmarshal(resp.Body, &out); err != nil {
		return nil, newApiError("expected a JSON array from /api/pedigrees: %v", err)
	}
	return out, nil
}

// GetPedigree returns the full pedigree detail.
func (c *Client) GetPedigree(ctx context.Context, pedigreeID string) (JSONObject, error) {
	path := fmt.Sprintf("/api/pedigrees/%s", pedigreeID)
	return c.getObject(ctx, path)
}

// DescribePedigree returns the server-rendered English description.
func (c *Client) DescribePedigree(ctx context.Context, pedigreeID string) (string, error) {
	path := fmt.Sprintf("/api/pedigrees/%s/describe", pedigreeID)
	resp, err := c.do(ctx, "GET", path, nil)
	if err != nil {
		return "", err
	}
	return resp.Text(), nil
}

// ListRiskModels returns the risk models this pedigree can run.
func (c *Client) ListRiskModels(ctx context.Context, pedigreeID string) (JSONObject, error) {
	path := fmt.Sprintf("/api/pedigrees/%s/risk/models", pedigreeID)
	return c.getObject(ctx, path)
}

// CalculateRiskArgs collects the inputs for [Client.CalculateRisk].
type CalculateRiskArgs struct {
	PedigreeID  string
	Model       string
	CounseleeID string // optional — empty string means "omit"
}

// CalculateRisk runs a named model against the pedigree.
func (c *Client) CalculateRisk(ctx context.Context, args CalculateRiskArgs) (JSONObject, error) {
	body := JSONObject{"model": args.Model}
	if args.CounseleeID != "" {
		body["counselee_id"] = args.CounseleeID
	}
	path := fmt.Sprintf("/api/pedigrees/%s/risk/calculate", args.PedigreeID)
	return c.postObject(ctx, path, body)
}

// CreateIndividualArgs collects the inputs for [Client.CreateIndividual].
type CreateIndividualArgs struct {
	DisplayName   string
	BiologicalSex string
}

// CreateIndividual creates a new individual record.
func (c *Client) CreateIndividual(ctx context.Context, args CreateIndividualArgs) (JSONObject, error) {
	body := JSONObject{
		"display_name":   args.DisplayName,
		"biological_sex": args.BiologicalSex,
	}
	return c.postObject(ctx, "/api/individuals", body)
}

// AddIndividualToPedigree attaches an existing individual to a pedigree.
func (c *Client) AddIndividualToPedigree(ctx context.Context, pedigreeID, individualID string) (JSONObject, error) {
	path := fmt.Sprintf("/api/pedigrees/%s/individuals/%s", pedigreeID, individualID)
	return c.postObject(ctx, path, JSONObject{})
}

// AddRelativeArgs collects the inputs for [Client.AddRelative].
type AddRelativeArgs struct {
	PedigreeID    string
	RelativeOf    string
	RelativeType  string
	DisplayName   string // may be empty
	BiologicalSex string // empty string means "omit"
}

// AddRelative posts to the register/add-relative convenience endpoint.
func (c *Client) AddRelative(ctx context.Context, args AddRelativeArgs) (JSONObject, error) {
	body := JSONObject{
		"relative_of":   args.RelativeOf,
		"relative_type": args.RelativeType,
		"display_name":  args.DisplayName,
	}
	if args.BiologicalSex != "" {
		body["biological_sex"] = args.BiologicalSex
	}
	path := fmt.Sprintf("/api/pedigrees/%s/register/add-relative", args.PedigreeID)
	return c.postObject(ctx, path, body)
}

// ------------------------------------------------------------------
// Transport helpers
// ------------------------------------------------------------------

func (c *Client) do(ctx context.Context, method, path string, body JSONObject) (httpgateway.Response, error) {
	req := httpgateway.Request{
		Method:  method,
		URL:     c.baseURL + path,
		Headers: c.headers(),
	}
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return httpgateway.Response{}, fmt.Errorf("encode body: %w", err)
		}
		req.Body = encoded
	}
	resp, err := c.http.Do(ctx, req)
	if err != nil {
		return httpgateway.Response{}, err
	}
	if resp.StatusCode < httpOKLower || resp.StatusCode >= httpOKUpper {
		return httpgateway.Response{}, newApiError(
			"Evagene API returned HTTP %d for %s", resp.StatusCode, path,
		)
	}
	return resp, nil
}

func (c *Client) getObject(ctx context.Context, path string) (JSONObject, error) {
	resp, err := c.do(ctx, "GET", path, nil)
	if err != nil {
		return nil, err
	}
	return decodeObject(resp.Body, path)
}

func (c *Client) postObject(ctx context.Context, path string, body JSONObject) (JSONObject, error) {
	resp, err := c.do(ctx, "POST", path, body)
	if err != nil {
		return nil, err
	}
	return decodeObject(resp.Body, path)
}

func (c *Client) headers() map[string]string {
	return map[string]string{
		"X-API-Key":    c.apiKey,
		"Content-Type": "application/json",
		"Accept":       "application/json",
	}
}

func decodeObject(raw []byte, path string) (JSONObject, error) {
	if len(raw) == 0 {
		return nil, newApiError("empty response body from %s", path)
	}
	var obj JSONObject
	if err := json.Unmarshal(raw, &obj); err != nil {
		return nil, newApiError("expected JSON object from %s: %v", path, err)
	}
	return obj, nil
}

// IsApiError reports whether err is an ApiError (direct or wrapped).
func IsApiError(err error) bool {
	var ae *ApiError
	return errors.As(err, &ae)
}
