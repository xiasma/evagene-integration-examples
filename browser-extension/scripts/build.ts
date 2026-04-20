/**
 * Build entry point. Bundles each extension entry with esbuild, then
 * copies the static manifest, HTML, CSS, and icons into dist/. Every
 * script referenced by manifest.json resolves to a file in dist/.
 */

import { context, build as esbuild } from 'esbuild';
import { copyFile, mkdir, readdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const srcDir = join(root, 'src');
const distDir = join(root, 'dist');
const iconsSrc = join(root, 'icons');
const iconsDist = join(distDir, 'icons');

const entryPoints = {
  background: join(srcDir, 'background.ts'),
  content: join(srcDir, 'content.ts'),
  sidePanel: join(srcDir, 'sidePanel.ts'),
  options: join(srcDir, 'options.ts'),
};

const STATIC_FILES: readonly string[] = [
  'manifest.json',
  'src/sidePanel.html',
  'src/sidePanel.css',
  'src/options.html',
];

async function main(): Promise<void> {
  const watch = process.argv.includes('--watch');
  await mkdir(distDir, { recursive: true });
  await copyStatics();
  await copyIcons();
  if (watch) {
    const ctx = await context(esbuildOptions());
    await ctx.watch();
    process.stdout.write('watching for changes...\n');
  } else {
    await esbuild(esbuildOptions());
    process.stdout.write('build complete\n');
  }
}

function esbuildOptions(): Parameters<typeof esbuild>[0] {
  return {
    entryPoints,
    outdir: distDir,
    bundle: true,
    format: 'esm',
    target: ['chrome114', 'firefox128'],
    platform: 'browser',
    sourcemap: true,
    logLevel: 'info',
  };
}

async function copyStatics(): Promise<void> {
  for (const relative of STATIC_FILES) {
    const src = join(root, relative);
    const dest = join(distDir, relative.replace(/^src\//, ''));
    await mkdir(dirname(dest), { recursive: true });
    await copyFile(src, dest);
  }
}

async function copyIcons(): Promise<void> {
  await mkdir(iconsDist, { recursive: true });
  const entries = await readdir(iconsSrc);
  for (const entry of entries) {
    await copyFile(join(iconsSrc, entry), join(iconsDist, entry));
  }
}

await main();
