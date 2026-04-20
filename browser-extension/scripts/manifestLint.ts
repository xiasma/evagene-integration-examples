/**
 * Headless substitute for loading the extension in a real browser.
 *
 * Validates manifest.json against a minimal MV3 schema, then asserts
 * every script/page referenced by the manifest exists in dist/.
 */

import { access, readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const distDir = join(root, 'dist');

interface Manifest {
  manifest_version?: unknown;
  background?: { service_worker?: unknown; type?: unknown };
  content_scripts?: readonly { js?: readonly unknown[] }[];
  side_panel?: { default_path?: unknown };
  options_ui?: { page?: unknown };
  icons?: Record<string, unknown>;
  permissions?: readonly unknown[];
  host_permissions?: readonly unknown[];
  browser_specific_settings?: { gecko?: { id?: unknown } };
}

async function main(): Promise<void> {
  const manifest = await readManifest();
  const problems: string[] = [];
  problems.push(...checkSchema(manifest));
  problems.push(...(await checkReferences(manifest)));
  if (problems.length > 0) {
    for (const problem of problems) process.stderr.write(`manifest-lint: ${problem}\n`);
    process.exit(1);
  }
  process.stdout.write('manifest-lint: ok\n');
}

async function readManifest(): Promise<Manifest> {
  const path = join(distDir, 'manifest.json');
  const raw = await readFile(path, 'utf8');
  return JSON.parse(raw) as Manifest;
}

function checkSchema(manifest: Manifest): readonly string[] {
  const problems: string[] = [];
  if (manifest.manifest_version !== 3) problems.push('manifest_version must be 3');
  if (typeof manifest.background?.service_worker !== 'string') {
    problems.push('background.service_worker must be a string');
  }
  if (manifest.background?.type !== 'module') {
    problems.push('background.type must be "module" for ESM workers');
  }
  if (!Array.isArray(manifest.content_scripts) || manifest.content_scripts.length === 0) {
    problems.push('content_scripts must be a non-empty array');
  }
  if (typeof manifest.side_panel?.default_path !== 'string') {
    problems.push('side_panel.default_path must be a string');
  }
  if (typeof manifest.options_ui?.page !== 'string') {
    problems.push('options_ui.page must be a string');
  }
  if (typeof manifest.browser_specific_settings?.gecko?.id !== 'string') {
    problems.push('browser_specific_settings.gecko.id must be set for Firefox compatibility');
  }
  return problems;
}

async function checkReferences(manifest: Manifest): Promise<readonly string[]> {
  const referenced = collectReferences(manifest);
  const problems: string[] = [];
  for (const relative of referenced) {
    const full = join(distDir, relative);
    try {
      await access(full);
    } catch {
      problems.push(`referenced file missing in dist/: ${relative}`);
    }
  }
  return problems;
}

function collectReferences(manifest: Manifest): readonly string[] {
  const refs: string[] = [];
  if (typeof manifest.background?.service_worker === 'string') {
    refs.push(manifest.background.service_worker);
  }
  for (const entry of manifest.content_scripts ?? []) {
    for (const script of entry.js ?? []) {
      if (typeof script === 'string') refs.push(script);
    }
  }
  if (typeof manifest.side_panel?.default_path === 'string') {
    refs.push(manifest.side_panel.default_path);
  }
  if (typeof manifest.options_ui?.page === 'string') {
    refs.push(manifest.options_ui.page);
  }
  for (const [, value] of Object.entries(manifest.icons ?? {})) {
    if (typeof value === 'string') refs.push(value);
  }
  return refs;
}

await main();
