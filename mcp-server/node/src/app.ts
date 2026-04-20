import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

import { ConfigError, loadConfig } from './config.js';
import { EvageneClient } from './evageneClient.js';
import { FetchHttpGateway } from './httpGateway.js';
import { StreamLogger } from './logger.js';
import { buildServer } from './server.js';

const EXIT_USAGE = 64;

export interface Streams {
  readonly stderr: NodeJS.WritableStream;
}

export async function run(
  env: Readonly<Record<string, string | undefined>>,
  streams: Streams,
): Promise<number> {
  try {
    const config = loadConfig(env);
    const logger = new StreamLogger(streams.stderr);
    const client = new EvageneClient({
      baseUrl: config.baseUrl,
      apiKey: config.apiKey,
      http: new FetchHttpGateway(),
    });
    const server = buildServer(client, logger);
    const transport = new StdioServerTransport();
    await server.connect(transport);
    logger.info(`evagene-mcp connected (baseUrl=${config.baseUrl})`);

    // Keep the process alive until the transport closes.
    await new Promise<void>((resolve) => {
      transport.onclose = (): void => { resolve(); };
    });
    return 0;
  } catch (error) {
    if (error instanceof ConfigError) {
      streams.stderr.write(`evagene-mcp: ${error.message}\n`);
      return EXIT_USAGE;
    }
    throw error;
  }
}
