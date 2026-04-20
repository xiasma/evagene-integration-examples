package httpgateway

import "context"

// Fake is an in-memory Gateway that records every call and returns a
// scripted response.  It lives in a non-test file so downstream test
// suites (evagene, tools, server) can import it without duplicating
// the same double.
type Fake struct {
	Calls    []Request
	Response Response
	Err      error
}

// Do records the request and returns the fake's scripted response.
func (f *Fake) Do(_ context.Context, req Request) (Response, error) {
	f.Calls = append(f.Calls, req)
	return f.Response, f.Err
}
