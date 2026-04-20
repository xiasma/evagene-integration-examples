/**
 * In-process publish/subscribe hub.
 *
 * One concern: deliver a sequence of domain events to any number of
 * live subscribers.  Subscribers only ever see events published *after*
 * they subscribe — this matches the semantics of Server-Sent Events
 * (clients that join late pick up the next delivery, not the backlog).
 *
 * Framework-free on purpose so it can be driven equally by the webhook
 * handler (publisher) and the Express SSE route adapter (subscriber).
 */

export interface DashboardEvent {
  readonly id: number;
  readonly eventType: string;
  readonly receivedAt: string;
  readonly body: string;
}

export type Subscriber = (event: DashboardEvent) => void;

export interface EventPublisher {
  publish(event: DashboardEvent): void;
}

export interface EventSubscriptionHub {
  subscribe(subscriber: Subscriber): () => void;
}

export class SseBroker implements EventPublisher, EventSubscriptionHub {
  private readonly subscribers = new Set<Subscriber>();

  subscribe(subscriber: Subscriber): () => void {
    this.subscribers.add(subscriber);
    return () => {
      this.subscribers.delete(subscriber);
    };
  }

  publish(event: DashboardEvent): void {
    for (const subscriber of this.subscribers) {
      subscriber(event);
    }
  }

  get size(): number {
    return this.subscribers.size;
  }
}
