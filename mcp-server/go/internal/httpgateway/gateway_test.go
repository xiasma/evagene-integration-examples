package httpgateway

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNetHTTP_SendsHeadersAndBody(t *testing.T) {
	var gotMethod, gotPath, gotHeader string
	var gotBody []byte
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		gotHeader = r.Header.Get("X-API-Key")
		gotBody, _ = io.ReadAll(r.Body)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))
	}))
	defer ts.Close()

	g := NewNetHTTP(2 * time.Second)
	resp, err := g.Do(context.Background(), Request{
		Method:  "POST",
		URL:     ts.URL + "/api/pedigrees",
		Headers: map[string]string{"X-API-Key": "evg_test"},
		Body:    []byte(`{"hello":"world"}`),
	})
	if err != nil {
		t.Fatalf("Do() err = %v", err)
	}

	if gotMethod != "POST" {
		t.Errorf("method = %q, want POST", gotMethod)
	}
	if gotPath != "/api/pedigrees" {
		t.Errorf("path = %q", gotPath)
	}
	if gotHeader != "evg_test" {
		t.Errorf("X-API-Key = %q", gotHeader)
	}
	if string(gotBody) != `{"hello":"world"}` {
		t.Errorf("body = %q", string(gotBody))
	}
	if resp.StatusCode != http.StatusOK {
		t.Errorf("status = %d", resp.StatusCode)
	}

	var parsed map[string]bool
	if err := resp.JSON(&parsed); err != nil {
		t.Fatalf("JSON() err = %v", err)
	}
	if !parsed["ok"] {
		t.Errorf("parsed = %+v", parsed)
	}
}

func TestResponse_Text(t *testing.T) {
	r := Response{StatusCode: 200, Body: []byte("hello")}
	if r.Text() != "hello" {
		t.Errorf("Text() = %q", r.Text())
	}
}

func TestFake_RecordsCallAndReturnsScriptedResponse(t *testing.T) {
	f := &Fake{Response: Response{StatusCode: 204}}
	resp, err := f.Do(context.Background(), Request{Method: "GET", URL: "u"})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if resp.StatusCode != 204 {
		t.Errorf("status = %d", resp.StatusCode)
	}
	if len(f.Calls) != 1 || f.Calls[0].URL != "u" {
		t.Errorf("calls = %+v", f.Calls)
	}
}
