package logger

import (
	"bytes"
	"strings"
	"testing"
	"time"
)

func frozenClock() Clock {
	fixed := time.Date(2026, 4, 20, 12, 0, 0, 0, time.UTC)
	return func() time.Time { return fixed }
}

func TestStream_Info(t *testing.T) {
	var buf bytes.Buffer
	NewWithClock(&buf, frozenClock()).Info("hello")

	got := buf.String()
	want := "2026-04-20T12:00:00Z INFO evagene-mcp: hello\n"
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestStream_Warn(t *testing.T) {
	var buf bytes.Buffer
	NewWithClock(&buf, frozenClock()).Warn("something dodgy")

	if !strings.Contains(buf.String(), "WARN evagene-mcp: something dodgy") {
		t.Errorf("missing WARN line: %q", buf.String())
	}
}
