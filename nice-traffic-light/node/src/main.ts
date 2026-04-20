#!/usr/bin/env node
import { run } from './app.js';

const exitCode = await run(process.argv.slice(2), process.env, {
  stdout: process.stdout,
  stderr: process.stderr,
});
process.exit(exitCode);
