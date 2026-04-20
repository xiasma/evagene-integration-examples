// Package logger writes structured log lines to an io.Writer.
//
// The composition root wires this to os.Stderr.  Stdout is the MCP
// transport — a stray write there corrupts the JSON-RPC framing — so
// the logger never accepts a Writer it does not own.
package logger

import (
	"fmt"
	"io"
	"time"
)

// Level is a severity tag printed with every line.
type Level string

const (
	LevelInfo  Level = "INFO"
	LevelWarn  Level = "WARN"
	LevelError Level = "ERROR"
)

// Clock returns the current time.  Injected so tests can assert output.
type Clock func() time.Time

// Stream is the minimal logger the server uses.
type Stream struct {
	w     io.Writer
	clock Clock
}

// New returns a Stream writing to w, using wall-clock time.
func New(w io.Writer) *Stream {
	return &Stream{w: w, clock: time.Now}
}

// NewWithClock is like [New] but with an injectable clock (for tests).
func NewWithClock(w io.Writer, clock Clock) *Stream {
	return &Stream{w: w, clock: clock}
}

// Info writes an INFO line.
func (s *Stream) Info(message string) { s.write(LevelInfo, message) }

// Warn writes a WARN line.
func (s *Stream) Warn(message string) { s.write(LevelWarn, message) }

// Error writes an ERROR line.
func (s *Stream) Error(message string) { s.write(LevelError, message) }

func (s *Stream) write(level Level, message string) {
	_, _ = fmt.Fprintf(
		s.w,
		"%s %s evagene-mcp: %s\n",
		s.clock().UTC().Format(time.RFC3339),
		level,
		message,
	)
}
