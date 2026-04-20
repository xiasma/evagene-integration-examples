import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

function loadEnv(): Record<string, string> {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
  const envFile = resolve(root, '.env');
  const out: Record<string, string> = {};
  for (const line of readFileSync(envFile, 'utf-8').split(/\r?\n/)) {
    if (line && !line.startsWith('#')) {
      const eq = line.indexOf('=');
      if (eq > 0) out[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
    }
  }
  return out;
}

async function main(): Promise<void> {
  const env = loadEnv();
  const serverScript = resolve(dirname(fileURLToPath(import.meta.url)), '../src/main.ts');

  const transport = new StdioClientTransport({
    command: process.execPath,
    args: ['--import', 'tsx', serverScript],
    env: {
      PATH: process.env.PATH ?? '',
      EVAGENE_API_KEY: env.EVAGENE_API_KEY ?? '',
      EVAGENE_BASE_URL: env.EVAGENE_BASE_URL ?? 'https://evagene.net',
    },
    stderr: 'inherit',
  });

  const client = new Client(
    { name: 'evagene-mcp-smoke', version: '0.1.0' },
    { capabilities: {} },
  );

  await client.connect(transport);
  process.stderr.write(`initialized: ${client.getServerVersion()?.name ?? '?'}\n`);

  const tools = await client.listTools();
  process.stderr.write(`tools: ${tools.tools.map((t) => t.name).join(', ')}\n`);

  const result = await client.callTool({ name: 'list_pedigrees', arguments: {} });
  const content = result.content as { type: string; text: string }[];
  for (const block of content) {
    if (block.type === 'text') process.stdout.write(block.text + '\n');
  }

  await client.close();
}

main().catch((err: unknown) => {
  process.stderr.write(`smoke test failed: ${String(err)}\n`);
  process.exit(1);
});
