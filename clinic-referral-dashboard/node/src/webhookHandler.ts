/**
 * Framework-agnostic webhook orchestration: verify signature, persist
 * via EventStore, fan-out to the SSE broker, produce an outcome.  The
 * Express adapter translates the outcome into an HTTP response.
 */

import type { AppendArgs, EventRow } from './eventStore.js';
import { verifySignature } from './signatureVerifier.js';
import type { DashboardEvent, EventPublisher } from './sseBroker.js';

export type WebhookOutcome =
  | { readonly status: 'accepted'; readonly rowId: number }
  | { readonly status: 'bad_signature' }
  | { readonly status: 'bad_request'; readonly reason: string };

export interface AppendOnlyStore {
  append(args: AppendArgs): EventRow;
}

export interface Clock {
  nowIso(): string;
}

export interface WebhookHandlerOptions {
  readonly secret: string;
  readonly store: AppendOnlyStore;
  readonly publisher: EventPublisher;
  readonly clock: Clock;
}

export interface IncomingDelivery {
  readonly rawBody: Buffer;
  readonly signatureHeader: string | undefined;
  readonly eventTypeHeader: string | undefined;
}

export class WebhookHandler {
  constructor(private readonly options: WebhookHandlerOptions) {}

  handle(delivery: IncomingDelivery): WebhookOutcome {
    if (!verifySignature(delivery.rawBody, delivery.signatureHeader, this.options.secret)) {
      return { status: 'bad_signature' };
    }
    const bodyText = delivery.rawBody.toString('utf8');
    if (!isJsonObject(bodyText)) {
      return { status: 'bad_request', reason: 'Body is not a JSON object.' };
    }
    const eventType = (delivery.eventTypeHeader ?? '').trim();
    if (!eventType) {
      return { status: 'bad_request', reason: 'Missing X-Evagene-Event header.' };
    }
    const row = this.options.store.append({
      receivedAt: this.options.clock.nowIso(),
      eventType,
      body: bodyText,
    });
    this.options.publisher.publish(toDashboardEvent(row));
    return { status: 'accepted', rowId: row.id };
  }
}

function toDashboardEvent(row: EventRow): DashboardEvent {
  return {
    id: row.id,
    eventType: row.eventType,
    receivedAt: row.receivedAt,
    body: row.body,
  };
}

function isJsonObject(text: string): boolean {
  try {
    const parsed: unknown = JSON.parse(text);
    return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed);
  } catch {
    return false;
  }
}
