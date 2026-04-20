package config

import (
	"errors"
	"testing"
)

func lookupFrom(env map[string]string) Lookup {
	return func(key string) (string, bool) {
		v, ok := env[key]
		return v, ok
	}
}

func TestLoad(t *testing.T) {
	tests := []struct {
		name        string
		env         map[string]string
		wantBaseURL string
		wantAPIKey  string
		wantErr     error
	}{
		{
			name:        "reads api key and defaults base url",
			env:         map[string]string{"EVAGENE_API_KEY": "evg_test"},
			wantBaseURL: DefaultBaseURL,
			wantAPIKey:  "evg_test",
		},
		{
			name: "overrides base url when set",
			env: map[string]string{
				"EVAGENE_API_KEY":  "evg_test",
				"EVAGENE_BASE_URL": "http://localhost:8000",
			},
			wantBaseURL: "http://localhost:8000",
			wantAPIKey:  "evg_test",
		},
		{
			name:    "rejects missing api key",
			env:     map[string]string{},
			wantErr: ErrMissingAPIKey,
		},
		{
			name:    "rejects blank api key",
			env:     map[string]string{"EVAGENE_API_KEY": "   "},
			wantErr: ErrMissingAPIKey,
		},
		{
			name: "falls back to default when base url is blank",
			env: map[string]string{
				"EVAGENE_API_KEY":  "evg_test",
				"EVAGENE_BASE_URL": "   ",
			},
			wantBaseURL: DefaultBaseURL,
			wantAPIKey:  "evg_test",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := Load(lookupFrom(tc.env))
			if tc.wantErr != nil {
				if !errors.Is(err, tc.wantErr) {
					t.Fatalf("Load() err = %v, want %v", err, tc.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("Load() err = %v, want nil", err)
			}
			if got.BaseURL != tc.wantBaseURL {
				t.Errorf("BaseURL = %q, want %q", got.BaseURL, tc.wantBaseURL)
			}
			if got.APIKey != tc.wantAPIKey {
				t.Errorf("APIKey = %q, want %q", got.APIKey, tc.wantAPIKey)
			}
		})
	}
}
