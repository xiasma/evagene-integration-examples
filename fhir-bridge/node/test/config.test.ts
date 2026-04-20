import { deepStrictEqual, strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, loadConfig } from '../src/config.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const PATIENT_ID = 'patient-42';

test('push requires a UUID pedigree id and a --to flag', () => {
  const config = loadConfig(
    ['push', PEDIGREE_ID, '--to', 'https://fhir.example/fhir'],
    { EVAGENE_API_KEY: 'evg_test' },
  );

  deepStrictEqual(config, {
    mode: 'push',
    subject: PEDIGREE_ID,
    fhirBaseUrl: 'https://fhir.example/fhir',
    evageneBaseUrl: 'https://evagene.net',
    evageneApiKey: 'evg_test',
  });
});

test('pull accepts any non-empty id and a --from flag', () => {
  const config = loadConfig(
    ['pull', PATIENT_ID, '--from', 'https://fhir.example/fhir', '--auth-header', 'Authorization: Bearer xyz'],
    { EVAGENE_API_KEY: 'evg_test' },
  );

  strictEqual(config.mode, 'pull');
  strictEqual(config.subject, PATIENT_ID);
  strictEqual(config.fhirAuthHeader, 'Authorization: Bearer xyz');
});

test('missing subcommand is rejected', () => {
  throws(
    () => loadConfig([], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});

test('push rejects a non-UUID pedigree id', () => {
  throws(
    () =>
      loadConfig(['push', 'not-a-uuid', '--to', 'https://fhir.example/fhir'], {
        EVAGENE_API_KEY: 'evg_test',
      }),
    ConfigError,
  );
});

test('missing API key is rejected', () => {
  throws(
    () =>
      loadConfig(['push', PEDIGREE_ID, '--to', 'https://fhir.example/fhir'], {}),
    ConfigError,
  );
});

test('missing --to is rejected', () => {
  throws(
    () => loadConfig(['push', PEDIGREE_ID], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});
