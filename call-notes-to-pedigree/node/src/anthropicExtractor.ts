/**
 * Extract an {@link ExtractedFamily} from a free-text transcript.
 * The extractor depends on an {@link LlmGateway} abstraction; the concrete
 * gateway wraps the official Anthropic SDK.
 */

import Anthropic from '@anthropic-ai/sdk';

import type { ExtractedFamily } from './extractedFamily.js';
import {
  ExtractionSchemaError,
  SYSTEM_PROMPT,
  type ToolSchema,
  buildToolSchema,
  parseExtraction,
} from './extractionSchema.js';

export const DEFAULT_MODEL = 'claude-sonnet-4-6';
const DEFAULT_MAX_TOKENS = 2048;

export class LlmUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'LlmUnavailableError';
  }
}

export interface LlmRequest {
  readonly model: string;
  readonly systemPrompt: string;
  readonly userPrompt: string;
  readonly tool: ToolSchema;
  readonly maxTokens: number;
  readonly temperature: number;
}

export interface LlmGateway {
  invokeTool(request: LlmRequest): Promise<Record<string, unknown>>;
}

export interface AnthropicExtractorOptions {
  readonly gateway: LlmGateway;
  readonly model?: string;
}

export class AnthropicExtractor {
  private readonly gateway: LlmGateway;
  private readonly model: string;

  constructor(options: AnthropicExtractorOptions) {
    this.gateway = options.gateway;
    this.model = options.model ?? DEFAULT_MODEL;
  }

  async extract(transcript: string): Promise<ExtractedFamily> {
    const input = await this.gateway.invokeTool({
      model: this.model,
      systemPrompt: SYSTEM_PROMPT,
      userPrompt: transcript,
      tool: buildToolSchema(),
      maxTokens: DEFAULT_MAX_TOKENS,
      temperature: 0,
    });
    return parseExtraction(input);
  }
}

export class AnthropicGateway implements LlmGateway {
  private readonly client: Anthropic;

  constructor(apiKey: string) {
    this.client = new Anthropic({ apiKey });
  }

  async invokeTool(request: LlmRequest): Promise<Record<string, unknown>> {
    let response;
    try {
      response = await this.client.messages.create({
        model: request.model,
        max_tokens: request.maxTokens,
        temperature: request.temperature,
        system: request.systemPrompt,
        tools: [request.tool],
        tool_choice: { type: 'tool', name: request.tool.name },
        messages: [{ role: 'user', content: request.userPrompt }],
      });
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new LlmUnavailableError(`Anthropic API call failed: ${reason}`);
    }
    return extractToolInput(response.content, request.tool.name);
  }
}

interface ToolUseBlock {
  readonly type: 'tool_use';
  readonly name: string;
  readonly input: unknown;
}

function extractToolInput(
  content: readonly unknown[],
  toolName: string,
): Record<string, unknown> {
  for (const block of content) {
    if (isToolUseBlock(block) && block.name === toolName) {
      if (
        typeof block.input !== 'object' ||
        block.input === null ||
        Array.isArray(block.input)
      ) {
        throw new ExtractionSchemaError(
          `Tool-use block for '${toolName}' did not carry an object input.`,
        );
      }
      return block.input as Record<string, unknown>;
    }
  }
  throw new ExtractionSchemaError(
    `Anthropic response did not include a tool_use block for '${toolName}'.`,
  );
}

function isToolUseBlock(block: unknown): block is ToolUseBlock {
  return (
    typeof block === 'object' &&
    block !== null &&
    (block as { type?: unknown }).type === 'tool_use' &&
    typeof (block as { name?: unknown }).name === 'string'
  );
}
