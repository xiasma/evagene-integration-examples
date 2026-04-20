import type { TrafficLightReport } from './trafficLight.js';

export interface TextSink {
  write(text: string): void;
}

export function present(report: TrafficLightReport, sink: TextSink): void {
  sink.write(`${report.colour.padEnd(6, ' ')} ${report.headline}\n`);
  for (const trigger of report.outcome.triggers) {
    sink.write(`  - ${trigger}\n`);
  }
}
