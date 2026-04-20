#!/usr/bin/env node
import { run } from './app.js';

const exitCode = await run(process.env, { stderr: process.stderr });
process.exit(exitCode);
