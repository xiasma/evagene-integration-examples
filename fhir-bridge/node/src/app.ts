/**
 * Composition root. Wires CLI -> Config -> clients -> handler, and maps
 * the handler's outcome to a Unix exit code.
 */

import { ConfigError, type Config, loadConfig } from './config.js';
import { EvageneApiError, EvageneClient } from './evageneClient.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { FhirApiError, FhirClient } from './fhirClient.js';
import { fhirBundleToIntakeFamily } from './fhirToIntake.js';
import { IntakeService } from './intakeService.js';
import { MappingError, pedigreeToFhirBundle } from './pedigreeToFhir.js';
import { parsePedigreeDetail } from './pedigreeDetail.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_NETWORK = 69;
export const EXIT_MAPPING = 70;

export interface TextSink {
  write(text: string): void;
}

export interface Streams {
  readonly stdout: TextSink;
  readonly stderr: TextSink;
}

export async function run(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
  streams: Streams,
  gateway?: HttpGateway,
): Promise<number> {
  let config: Config;
  try {
    config = loadConfig(argv, env);
  } catch (error) {
    if (error instanceof ConfigError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_USAGE;
    }
    throw error;
  }

  const http = gateway ?? new FetchHttpGateway();
  const handler = buildHandler(config, http, streams.stdout);
  return executeSafely(handler, streams);
}

type Handler = () => Promise<void>;

function buildHandler(config: Config, http: HttpGateway, stdout: TextSink): Handler {
  const evagene = new EvageneClient({
    baseUrl: config.evageneBaseUrl,
    apiKey: config.evageneApiKey,
    http,
  });
  const fhir = new FhirClient(
    config.fhirAuthHeader === undefined
      ? { baseUrl: config.fhirBaseUrl, http }
      : { baseUrl: config.fhirBaseUrl, http, authHeader: config.fhirAuthHeader },
  );
  const intake = new IntakeService({ client: evagene });

  return config.mode === 'push'
    ? () => pushPedigree(config.subject, evagene, fhir, stdout)
    : () => pullPedigree(config.subject, fhir, intake, stdout);
}

async function executeSafely(action: Handler, streams: Streams): Promise<number> {
  try {
    await action();
    return EXIT_OK;
  } catch (error) {
    if (error instanceof EvageneApiError || error instanceof FhirApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_NETWORK;
    }
    if (error instanceof MappingError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_MAPPING;
    }
    throw error;
  }
}

async function pushPedigree(
  pedigreeId: string,
  evagene: EvageneClient,
  fhir: FhirClient,
  stdout: TextSink,
): Promise<void> {
  const raw = await evagene.getPedigreeDetail(pedigreeId);
  const detail = parsePedigreeDetail(raw);
  const mapping = pedigreeToFhirBundle(detail);
  for (const warning of mapping.warnings) {
    stdout.write(`warning: ${warning}\n`);
  }
  const response = await fhir.postTransactionBundle(mapping.bundle);
  const responseEntries = response.entry ?? [];
  stdout.write(`POST Bundle -> ${responseEntries.length.toString()} response entries\n`);
  for (const entry of responseEntries) {
    if (entry.response?.location !== undefined) {
      stdout.write(`${entry.response.location}\n`);
    }
  }
  stdout.write(
    `wrote ${(mapping.bundle.entry ?? []).length.toString()} FamilyMemberHistory resources\n`,
  );
}

async function pullPedigree(
  patientId: string,
  fhir: FhirClient,
  intake: IntakeService,
  stdout: TextSink,
): Promise<void> {
  const bundle = await fhir.fetchFamilyHistoryForPatient(patientId);
  const entryCount = (bundle.entry ?? []).length;
  stdout.write(
    `GET FamilyMemberHistory?patient=${patientId} -> ${entryCount.toString()} entries\n`,
  );
  const mapping = fhirBundleToIntakeFamily(bundle, { patientId });
  for (const warning of mapping.warnings) {
    stdout.write(`warning: ${warning}\n`);
  }
  const result = await intake.create(mapping.family);
  stdout.write(`pedigree created: ${result.pedigreeId}\n`);
  stdout.write(`proband:          ${result.probandId}\n`);
  stdout.write(`relatives added:  ${result.relativesAdded.toString()}\n`);
}
