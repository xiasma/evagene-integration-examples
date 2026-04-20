#!/usr/bin/env node
import { EXIT_SOFTWARE, run } from './app.js';

try {
  const exitCode = await run(process.argv.slice(2), process.env, {
    stdout: process.stdout,
    stderr: process.stderr,
  });
  process.exit(exitCode);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`error: ${message}\n`);
  process.exit(EXIT_SOFTWARE);
}
