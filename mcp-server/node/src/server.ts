// We use the low-level `Server` class rather than `McpServer` because our
// tool inputs are expressed as raw JSON Schema (the MCP wire format).
// `McpServer.registerTool` only accepts Zod schemas.  This is the exact
// case the upstream deprecation notice calls out as "advanced use".
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolResult,
  type ListToolsResult,
  type Tool,
} from '@modelcontextprotocol/sdk/types.js';

import { ApiError } from './evageneClient.js';
import {
  TOOL_SPECS,
  ToolArgumentError,
  type EvageneClientPort,
  handleCall,
} from './toolHandlers.js';

export const SERVER_NAME = 'evagene';
export const SERVER_VERSION = '0.1.0';

export interface StructuredLogger {
  info(message: string): void;
  warn(message: string): void;
}

// eslint-disable-next-line @typescript-eslint/no-deprecated
export function buildServer(client: EvageneClientPort, logger: StructuredLogger): Server {
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, (): ListToolsResult => ({
    tools: TOOL_SPECS.map((spec): Tool => ({
      name: spec.name,
      description: spec.description,
      inputSchema: spec.inputSchema as Tool['inputSchema'],
    })),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request): Promise<CallToolResult> => {
    const name = request.params.name;
    const args = request.params.arguments ?? {};

    try {
      const result = await handleCall(client, name, args);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      if (error instanceof ToolArgumentError) {
        return errorResult(`Invalid arguments: ${error.message}`);
      }
      if (error instanceof ApiError) {
        logger.warn(`Evagene API error for tool ${name}: ${error.message}`);
        return errorResult(error.message);
      }
      throw error;
    }
  });

  return server;
}

function errorResult(message: string): CallToolResult {
  return {
    isError: true,
    content: [{ type: 'text', text: `Error: ${message}` }],
  };
}
