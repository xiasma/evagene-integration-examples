export interface Clock {
  nowIso(): string;
  nowEpochSeconds(): number;
}

export class SystemClock implements Clock {
  nowIso(): string {
    return new Date().toISOString();
  }

  nowEpochSeconds(): number {
    return Math.floor(Date.now() / 1000);
  }
}
