import type { NiceOutcome, RiskCategory } from './classifier.js';

export type TrafficLight = 'GREEN' | 'AMBER' | 'RED';

export interface TrafficLightReport {
  readonly colour: TrafficLight;
  readonly headline: string;
  readonly outcome: NiceOutcome;
}

const COLOUR_BY_CATEGORY: Readonly<Record<RiskCategory, TrafficLight>> = {
  near_population: 'GREEN',
  moderate: 'AMBER',
  high: 'RED',
};

const HEADLINE_BY_CATEGORY: Readonly<Record<RiskCategory, (name: string) => string>> = {
  near_population: name =>
    `Near-population risk for ${name} \u2014 no enhanced surveillance required.`,
  moderate: name => `Moderate risk for ${name} \u2014 refer if further history emerges.`,
  high: name => `High risk for ${name} \u2014 refer for genetics assessment.`,
};

export function toTrafficLight(outcome: NiceOutcome): TrafficLightReport {
  const name = outcome.counseleeName || 'counselee';
  return {
    colour: COLOUR_BY_CATEGORY[outcome.category],
    headline: HEADLINE_BY_CATEGORY[outcome.category](name),
    outcome,
  };
}
