import type { StructuredLogger } from './server.js';

/**
 * Writes log lines to a stream — **always stderr in production**, since
 * stdout is the MCP transport.  Injecting the stream keeps the module
 * testable and prevents an accidental `console.log` from corrupting the
 * protocol.
 */
export class StreamLogger implements StructuredLogger {
  constructor(private readonly stream: NodeJS.WritableStream) {}

  info(message: string): void {
    this.write('INFO', message);
  }

  warn(message: string): void {
    this.write('WARN', message);
  }

  private write(level: string, message: string): void {
    this.stream.write(`${new Date().toISOString()} ${level} evagene-mcp: ${message}\n`);
  }
}
