import { strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

import { SERVER_NAME, SERVER_VERSION, buildServer } from '../src/server.js';

import { FakeClient } from './fakes.js';

function silentLogger(): { info: () => void; warn: () => void } {
  return { info: (): void => undefined, warn: (): void => undefined };
}

async function connect(
  client: FakeClient,
): Promise<Client> {
  const server = buildServer(client, silentLogger());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  const mcpClient = new Client(
    { name: 'evagene-mcp-tests', version: '0.1.0' },
    { capabilities: {} },
  );

  await Promise.all([
    server.connect(serverTransport),
    mcpClient.connect(clientTransport),
  ]);
  return mcpClient;
}

test('list_tools exposes every spec', async () => {
  const client = new FakeClient();
  const mcpClient = await connect(client);

  const result = await mcpClient.listTools();

  const names = new Set(result.tools.map((t) => t.name));
  for (const expected of [
    'list_pedigrees',
    'get_pedigree',
    'describe_pedigree',
    'list_risk_models',
    'calculate_risk',
    'add_individual',
    'add_relative',
  ]) {
    strictEqual(names.has(expected), true, `missing tool: ${expected}`);
  }
  await mcpClient.close();
});

test('call_tool list_pedigrees round-trips JSON', async () => {
  const client = new FakeClient();
  client.listPedigreesResult = [
    { id: 'p1', display_name: 'Fam' },
  ];
  const mcpClient = await connect(client);

  const result = await mcpClient.callTool({ name: 'list_pedigrees', arguments: {} });

  const content = result.content as { type: string; text: string }[];
  strictEqual(content[0]?.type, 'text');
  const parsed = JSON.parse(content[0].text) as unknown;
  strictEqual(Array.isArray(parsed), true);
  await mcpClient.close();
});

test('server metadata advertises SERVER_NAME', () => {
  strictEqual(SERVER_NAME, 'evagene');
  strictEqual(SERVER_VERSION, '0.1.0');
});
