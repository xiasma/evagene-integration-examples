// Package config loads the server's immutable configuration from the
// environment.
//
// The MCP server is started by a client (Claude Desktop, Cursor, etc.)
// which injects the API key via the host's config stanza — there are no
// command-line flags to parse.
package config

import (
	"errors"
	"strings"
)

// DefaultBaseURL is used when EVAGENE_BASE_URL is unset or blank.
const DefaultBaseURL = "https://evagene.net"

// ErrMissingAPIKey is returned when EVAGENE_API_KEY is absent or blank.
var ErrMissingAPIKey = errors.New("EVAGENE_API_KEY environment variable is required")

// Config is the immutable value object consumed by the composition root.
type Config struct {
	BaseURL string
	APIKey  string
}

// Lookup returns the value for key, reporting whether it was present.
// It mirrors os.LookupEnv so callers can inject a fake in tests.
type Lookup func(key string) (string, bool)

// Load reads Config from the provided lookup.
func Load(lookup Lookup) (Config, error) {
	apiKey := strings.TrimSpace(stringFor(lookup, "EVAGENE_API_KEY"))
	if apiKey == "" {
		return Config{}, ErrMissingAPIKey
	}

	baseURL := strings.TrimSpace(stringFor(lookup, "EVAGENE_BASE_URL"))
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}
	return Config{BaseURL: baseURL, APIKey: apiKey}, nil
}

func stringFor(lookup Lookup, key string) string {
	if v, ok := lookup(key); ok {
		return v
	}
	return ""
}
