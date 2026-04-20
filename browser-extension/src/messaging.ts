/**
 * Typed message envelopes exchanged between content script, background
 * service worker, and side panel.
 *
 * Content scripts must not make cross-origin requests directly in MV3 —
 * every network call is routed through the background worker, which owns
 * the API key. The union here is the contract between the three scripts.
 */

export interface LookupRequest {
  readonly kind: 'lookup-pedigree';
  readonly pedigreeId: string;
}

export interface PedigreeSummary {
  readonly pedigreeId: string;
  readonly name: string;
  readonly probandName: string | null;
  readonly diseases: readonly string[];
  readonly viewUrl: string;
}

export interface LookupSuccess {
  readonly kind: 'lookup-result';
  readonly ok: true;
  readonly summary: PedigreeSummary;
}

export interface LookupFailure {
  readonly kind: 'lookup-result';
  readonly ok: false;
  readonly error: string;
}

export type LookupResponse = LookupSuccess | LookupFailure;

export type Message = LookupRequest;
export type Response = LookupResponse;

export type Handler<M extends Message> = (message: M) => Promise<Response>;

export type HandlerMap = {
  readonly [K in Message['kind']]: Handler<Extract<Message, { kind: K }>>;
};

export function route(message: unknown, handlers: HandlerMap): Promise<Response> {
  if (!isMessage(message)) {
    return Promise.resolve(failure('Unknown message envelope'));
  }
  const handler = handlers[message.kind];
  return handler(message);
}

export function failure(error: string): LookupFailure {
  return { kind: 'lookup-result', ok: false, error };
}

function isMessage(value: unknown): value is Message {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as { kind?: unknown; pedigreeId?: unknown };
  return (
    candidate.kind === 'lookup-pedigree' && typeof candidate.pedigreeId === 'string'
  );
}
