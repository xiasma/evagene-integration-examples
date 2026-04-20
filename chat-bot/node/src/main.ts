#!/usr/bin/env node
import { ConfigError, buildApp } from './app.js';

try {
  buildApp(process.argv.slice(2), process.env).start();
} catch (error) {
  if (error instanceof ConfigError) {
    process.stderr.write(`error: ${error.message}\n`);
    process.exit(64);
  }
  throw error;
}
