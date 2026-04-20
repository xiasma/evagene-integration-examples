/**
 * Options page. Persists the API key, base URL, and patient-ID regex to
 * `chrome.storage.local`. Rejects regexes that would overmatch common
 * short tokens on the page — see patternValidator for the rationale.
 */

import { validatePattern } from './patternValidator.js';
import { readSettings, writeSettings } from './storage.js';

interface Form {
  readonly apiKey: HTMLInputElement;
  readonly baseUrl: HTMLInputElement;
  readonly patternSource: HTMLInputElement;
  readonly status: HTMLElement;
  readonly error: HTMLElement;
  readonly form: HTMLFormElement;
}

function bind(): Form {
  return {
    apiKey: requireInput('apiKey'),
    baseUrl: requireInput('baseUrl'),
    patternSource: requireInput('patternSource'),
    status: requireElement('status'),
    error: requireElement('error'),
    form: requireElement('form') as HTMLFormElement,
  };
}

function requireElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (element === null) throw new Error(`Missing #${id}`);
  return element;
}

function requireInput(id: string): HTMLInputElement {
  const element = requireElement(id);
  if (!(element instanceof HTMLInputElement)) {
    throw new Error(`#${id} is not an input`);
  }
  return element;
}

async function load(form: Form): Promise<void> {
  const settings = await readSettings();
  form.apiKey.value = settings.apiKey;
  form.baseUrl.value = settings.baseUrl;
  form.patternSource.value = settings.patternSource;
}

async function save(form: Form): Promise<void> {
  form.status.hidden = true;
  form.error.hidden = true;
  const validation = validatePattern(form.patternSource.value);
  if (!validation.ok) {
    form.error.hidden = false;
    form.error.textContent = validation.error;
    return;
  }
  await writeSettings({
    apiKey: form.apiKey.value.trim(),
    baseUrl: form.baseUrl.value.trim(),
    patternSource: form.patternSource.value.trim(),
  });
  form.status.hidden = false;
  form.status.textContent = 'Saved.';
}

async function init(): Promise<void> {
  const form = bind();
  await load(form);
  form.form.addEventListener('submit', event => {
    event.preventDefault();
    void save(form);
  });
}

void init();
