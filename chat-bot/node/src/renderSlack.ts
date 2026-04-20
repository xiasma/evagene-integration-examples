/**
 * Pure: (ChatReport) -> Slack in_channel response JSON.
 *
 * Slack ignores unknown fields, so we keep the payload to blocks Slack
 * definitely renders: header, section, context. The SVG link is a plain
 * link (Slack does not render SVG inline); the web UI is offered as a
 * primary action button.
 */

import type { ChatReport } from './handlers.js';
import type { NiceCategory } from './evageneClient.js';

type SlackBlock = Record<string, unknown>;

export interface SlackResponse {
  readonly response_type: 'in_channel';
  readonly text: string;
  readonly blocks: readonly SlackBlock[];
}

const CATEGORY_EMOJI: Readonly<Record<NiceCategory, string>> = {
  GREEN: ':large_green_circle:',
  AMBER: ':large_yellow_circle:',
  RED: ':red_circle:',
};

export function renderSlack(report: ChatReport): SlackResponse {
  const headline = headlineText(report);
  return {
    response_type: 'in_channel',
    text: headline,
    blocks: [
      headerBlock(headline),
      contextBlock(contextText(report)),
      categoryBlock(report),
      ...triggersBlock(report),
      linksBlock(report),
    ],
  };
}

export function renderSlackError(message: string): SlackResponse {
  return {
    response_type: 'in_channel',
    text: message,
    blocks: [
      {
        type: 'section',
        text: { type: 'mrkdwn', text: `:warning: ${message}` },
      },
    ],
  };
}

function headlineText(report: ChatReport): string {
  return `${report.summary.displayName} - NICE ${report.nice.category}`;
}

function contextText(report: ChatReport): string {
  return report.summary.probandName === undefined
    ? 'No proband designated.'
    : `Proband: ${report.summary.probandName}`;
}

function headerBlock(text: string): SlackBlock {
  return { type: 'header', text: { type: 'plain_text', text } };
}

function contextBlock(text: string): SlackBlock {
  return { type: 'context', elements: [{ type: 'mrkdwn', text }] };
}

function categoryBlock(report: ChatReport): SlackBlock {
  const emoji = CATEGORY_EMOJI[report.nice.category];
  const refer = report.nice.referForGeneticsAssessment
    ? 'Refer for genetics assessment.'
    : 'No referral indicated.';
  return {
    type: 'section',
    text: {
      type: 'mrkdwn',
      text: `${emoji} *NICE ${report.nice.category}* - ${refer}`,
    },
  };
}

function triggersBlock(report: ChatReport): readonly SlackBlock[] {
  if (report.nice.triggers.length === 0) {
    return [];
  }
  const bullets = report.nice.triggers.map(trigger => `- ${trigger}`).join('\n');
  return [
    {
      type: 'section',
      text: { type: 'mrkdwn', text: `*Triggers*\n${bullets}` },
    },
  ];
}

function linksBlock(report: ChatReport): SlackBlock {
  return {
    type: 'actions',
    elements: [
      {
        type: 'button',
        text: { type: 'plain_text', text: 'View pedigree' },
        url: report.links.webUrl,
      },
      {
        type: 'button',
        text: { type: 'plain_text', text: 'Download SVG' },
        url: report.links.svgUrl,
      },
    ],
  };
}
