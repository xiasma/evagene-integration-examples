/**
 * Pure: (ChatReport) -> Teams MessageCard JSON.
 *
 * Outgoing-webhook replies expect an `MessageCard`. We include the
 * pedigree name, proband, NICE category + triggers, and a single
 * `OpenUri` action to the pedigree's Evagene web page.
 */

import type { ChatReport } from './handlers.js';
import type { NiceCategory } from './evageneClient.js';

export interface TeamsResponse {
  readonly type: 'message';
  readonly '@type': 'MessageCard';
  readonly '@context': 'https://schema.org/extensions';
  readonly themeColor: string;
  readonly summary: string;
  readonly title: string;
  readonly text: string;
  readonly sections: readonly TeamsSection[];
  readonly potentialAction: readonly TeamsAction[];
}

interface TeamsSection {
  readonly activityTitle?: string;
  readonly activitySubtitle?: string;
  readonly text?: string;
  readonly facts?: readonly { readonly name: string; readonly value: string }[];
}

interface TeamsAction {
  readonly '@type': 'OpenUri';
  readonly name: string;
  readonly targets: readonly { readonly os: 'default'; readonly uri: string }[];
}

const THEME_BY_CATEGORY: Readonly<Record<NiceCategory, string>> = {
  GREEN: '2EB886',
  AMBER: 'F5A623',
  RED: 'D0021B',
};

export function renderTeams(report: ChatReport): TeamsResponse {
  const refer = report.nice.referForGeneticsAssessment
    ? 'Refer for genetics assessment.'
    : 'No referral indicated.';
  return {
    type: 'message',
    '@type': 'MessageCard',
    '@context': 'https://schema.org/extensions',
    themeColor: THEME_BY_CATEGORY[report.nice.category],
    summary: `${report.summary.displayName} - NICE ${report.nice.category}`,
    title: report.summary.displayName,
    text: `**NICE ${report.nice.category}** - ${refer}`,
    sections: [
      {
        facts: factsOf(report),
      },
      ...triggersSection(report),
    ],
    potentialAction: [
      {
        '@type': 'OpenUri',
        name: 'View pedigree',
        targets: [{ os: 'default', uri: report.links.webUrl }],
      },
      {
        '@type': 'OpenUri',
        name: 'Download SVG',
        targets: [{ os: 'default', uri: report.links.svgUrl }],
      },
    ],
  };
}

export function renderTeamsError(message: string): TeamsResponse {
  return {
    type: 'message',
    '@type': 'MessageCard',
    '@context': 'https://schema.org/extensions',
    themeColor: '888888',
    summary: message,
    title: 'Evagene bot',
    text: message,
    sections: [],
    potentialAction: [],
  };
}

function factsOf(report: ChatReport): readonly { readonly name: string; readonly value: string }[] {
  const facts: { readonly name: string; readonly value: string }[] = [
    { name: 'NICE category', value: report.nice.category },
  ];
  if (report.summary.probandName !== undefined) {
    facts.push({ name: 'Proband', value: report.summary.probandName });
  }
  return facts;
}

function triggersSection(report: ChatReport): readonly TeamsSection[] {
  if (report.nice.triggers.length === 0) {
    return [];
  }
  const bullets = report.nice.triggers.map(trigger => `- ${trigger}`).join('\n\n');
  return [{ activityTitle: '**Triggers**', text: bullets }];
}
