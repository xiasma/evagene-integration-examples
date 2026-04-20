// Package httpgateway defines a narrow HTTP abstraction used by the
// Evagene client.
//
// Keeping the interface minimal (one request method, one response shape)
// lets the client and its tests share a single point of transport
// control without pulling net/http into every test.
package httpgateway

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"
)

// Response is the portion of an HTTP response the Evagene client needs.
type Response struct {
	StatusCode int
	Body       []byte
}

// JSON decodes Body into v. It returns an error if the body is not JSON.
func (r Response) JSON(v any) error {
	if len(r.Body) == 0 {
		return errors.New("empty response body")
	}
	return json.Unmarshal(r.Body, v)
}

// Text returns the body as a string.
func (r Response) Text() string { return string(r.Body) }

// Request is the shape the Evagene client submits.
type Request struct {
	Method  string
	URL     string
	Headers map[string]string
	// Body is an already-encoded JSON body, or nil for no body.
	Body []byte
}

// Gateway is the one-method abstraction the client depends on.
type Gateway interface {
	Do(ctx context.Context, req Request) (Response, error)
}

// NetHTTP is the net/http-backed concrete Gateway.
type NetHTTP struct {
	client *http.Client
}

// NewNetHTTP returns a Gateway backed by net/http with the given timeout.
func NewNetHTTP(timeout time.Duration) *NetHTTP {
	return &NetHTTP{client: &http.Client{Timeout: timeout}}
}

// Do executes req and reads the response body into memory.
func (g *NetHTTP) Do(ctx context.Context, req Request) (Response, error) {
	var body io.Reader
	if len(req.Body) > 0 {
		body = bytes.NewReader(req.Body)
	}
	httpReq, err := http.NewRequestWithContext(ctx, req.Method, req.URL, body)
	if err != nil {
		return Response{}, err
	}
	for k, v := range req.Headers {
		httpReq.Header.Set(k, v)
	}

	resp, err := g.client.Do(httpReq)
	if err != nil {
		return Response{}, err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return Response{}, err
	}
	return Response{StatusCode: resp.StatusCode, Body: raw}, nil
}
