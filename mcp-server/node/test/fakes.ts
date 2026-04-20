import type {
  HttpGateway,
  HttpRequestOptions,
  HttpResponse,
} from '../src/httpGateway.js';
import type {
  AddRelativeArgs,
  CalculateRiskArgs,
  CreateIndividualArgs,
  JsonObject,
} from '../src/evageneClient.js';
import type { EvageneClientPort } from '../src/toolHandlers.js';

export interface StubResponseInit {
  readonly status: number;
  readonly jsonPayload?: unknown;
  readonly textPayload?: string;
}

export function stubResponse(init: StubResponseInit): HttpResponse {
  return {
    status: init.status,
    json: () => Promise.resolve(init.jsonPayload),
    text: () => Promise.resolve(init.textPayload ?? ''),
  };
}

export interface RecordedCall {
  readonly method: string;
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export class RecordingGateway implements HttpGateway {
  readonly calls: RecordedCall[] = [];

  constructor(private readonly responseFor: (url: string) => HttpResponse) {}

  request(url: string, options: HttpRequestOptions): Promise<HttpResponse> {
    this.calls.push({
      method: options.method,
      url,
      headers: options.headers,
      body: options.body,
    });
    return Promise.resolve(this.responseFor(url));
  }
}

export class FakeClient implements EvageneClientPort {
  listPedigreesResult: JsonObject[] = [];
  getPedigreeResult: JsonObject = {};
  describePedigreeResult = '';
  listRiskModelsResult: JsonObject = {};
  calculateRiskResult: JsonObject = {};
  createIndividualResult: JsonObject = {};
  addIndividualToPedigreeResult: JsonObject = {};
  addRelativeResult: JsonObject = {};

  readonly calls: (readonly [string, Record<string, unknown>])[] = [];

  listPedigrees(): Promise<JsonObject[]> {
    this.calls.push(['listPedigrees', {}]);
    return Promise.resolve(this.listPedigreesResult);
  }

  getPedigree(pedigreeId: string): Promise<JsonObject> {
    this.calls.push(['getPedigree', { pedigreeId }]);
    return Promise.resolve(this.getPedigreeResult);
  }

  describePedigree(pedigreeId: string): Promise<string> {
    this.calls.push(['describePedigree', { pedigreeId }]);
    return Promise.resolve(this.describePedigreeResult);
  }

  listRiskModels(pedigreeId: string): Promise<JsonObject> {
    this.calls.push(['listRiskModels', { pedigreeId }]);
    return Promise.resolve(this.listRiskModelsResult);
  }

  calculateRisk(args: CalculateRiskArgs): Promise<JsonObject> {
    this.calls.push(['calculateRisk', { ...args }]);
    return Promise.resolve(this.calculateRiskResult);
  }

  createIndividual(args: CreateIndividualArgs): Promise<JsonObject> {
    this.calls.push(['createIndividual', { ...args }]);
    return Promise.resolve(this.createIndividualResult);
  }

  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<JsonObject> {
    this.calls.push(['addIndividualToPedigree', { pedigreeId, individualId }]);
    return Promise.resolve(this.addIndividualToPedigreeResult);
  }

  addRelative(args: AddRelativeArgs): Promise<JsonObject> {
    this.calls.push(['addRelative', { ...args }]);
    return Promise.resolve(this.addRelativeResult);
  }
}
