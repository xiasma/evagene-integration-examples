/**
 * Read a transcript from a file path or from a stdin-like stream.
 */

import { readFile } from 'node:fs/promises';
import type { Readable } from 'node:stream';

export class TranscriptError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TranscriptError';
  }
}

export async function readFromPath(path: string): Promise<string> {
  let text: string;
  try {
    text = await readFile(path, 'utf8');
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new TranscriptError(`Could not read transcript ${path}: ${reason}`);
  }
  return requireNonEmpty(text, path);
}

export async function readFromStream(stream: Readable): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : (chunk as Buffer));
  }
  return requireNonEmpty(Buffer.concat(chunks).toString('utf8'), 'stdin');
}

function requireNonEmpty(text: string, source: string): string {
  if (text.trim() === '') {
    throw new TranscriptError(`Transcript from ${source} was empty.`);
  }
  return text;
}
