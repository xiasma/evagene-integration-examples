/**
 * Typed wrapper around `chrome.storage.local` for the handful of keys
 * this extension cares about. We use local storage (not sync) because
 * the API key is a secret and must not replicate across devices.
 */

export const DEFAULT_BASE_URL = 'https://evagene.net';
export const DEFAULT_PATTERN =
  '\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b';

export interface Settings {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly patternSource: string;
}

export async function readSettings(): Promise<Settings> {
  const stored = (await chrome.storage.local.get([
    'apiKey',
    'baseUrl',
    'patternSource',
  ]));
  return {
    apiKey: typeof stored.apiKey === 'string' ? stored.apiKey : '',
    baseUrl: typeof stored.baseUrl === 'string' && stored.baseUrl !== ''
      ? stored.baseUrl
      : DEFAULT_BASE_URL,
    patternSource:
      typeof stored.patternSource === 'string' && stored.patternSource !== ''
        ? stored.patternSource
        : DEFAULT_PATTERN,
  };
}

export async function writeSettings(settings: Settings): Promise<void> {
  await chrome.storage.local.set({
    apiKey: settings.apiKey,
    baseUrl: settings.baseUrl,
    patternSource: settings.patternSource,
  });
}
