import { deepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { mkdtempSync, readFileSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { CANRISK_HEADER } from '../src/canRiskClient.js';
import { type BrowserLauncher, OutputSink, filenameFor } from '../src/outputSink.js';

const PEDIGREE_ID = 'a1cfe665-2e95-4386-9eb8-53d46095478a';

class SpyBrowser implements BrowserLauncher {
  readonly opened: string[] = [];

  open(url: string): void {
    this.opened.push(url);
  }
}

function tempDir(): string {
  return mkdtempSync(join(tmpdir(), 'canrisk-bridge-'));
}

test('filename uses first eight chars of the UUID', () => {
  strictEqual(filenameFor(PEDIGREE_ID), 'evagene-canrisk-a1cfe665.txt');
});

test('save writes the payload to the named file in the output dir', () => {
  const dir = tempDir();
  const sink = new OutputSink({ outputDir: dir, browser: new SpyBrowser() });
  const payload = `${CANRISK_HEADER}\nFamID\tName\n`;

  const saved = sink.save(PEDIGREE_ID, payload);

  strictEqual(saved, join(dir, 'evagene-canrisk-a1cfe665.txt'));
  strictEqual(readFileSync(saved, 'utf8'), payload);
});

test('save creates the output dir if it does not exist', () => {
  const nested = join(tempDir(), 'nested', 'dir');
  const sink = new OutputSink({ outputDir: nested, browser: new SpyBrowser() });

  sink.save(PEDIGREE_ID, `${CANRISK_HEADER}\n`);

  ok(statSync(nested).isDirectory());
});

test('openUploadPage delegates to the injected browser', () => {
  const browser = new SpyBrowser();
  const sink = new OutputSink({ outputDir: tempDir(), browser });

  sink.openUploadPage();

  deepStrictEqual(browser.opened, ['https://canrisk.org']);
});
