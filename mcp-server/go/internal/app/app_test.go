package app

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

func TestRun_ExitsWithUsageWhenAPIKeyMissing(t *testing.T) {
	var stderr bytes.Buffer
	code := Run(context.Background(), func(string) (string, bool) { return "", false }, &stderr)

	if code != ExitUsage {
		t.Errorf("exit code = %d, want %d", code, ExitUsage)
	}
	if !strings.Contains(stderr.String(), "EVAGENE_API_KEY") {
		t.Errorf("stderr = %q", stderr.String())
	}
}
