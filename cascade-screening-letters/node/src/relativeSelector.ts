/**
 * Pure filter: RegisterData in, list of letter targets out.
 *
 * Selects first-degree (parent / child / sibling) and second-degree
 * (grandparent / aunt / uncle / nephew / niece / half-sibling) relatives.
 * Skips the proband, rows with no display name, and more-distant relatives.
 * Relationship labels may carry a side suffix such as "Aunt (maternal)".
 */

import type { RegisterData, RegisterRow } from './evageneClient.js';

const FIRST_DEGREE_BASES: ReadonlySet<string> = new Set([
  'Father',
  'Mother',
  'Parent',
  'Brother',
  'Sister',
  'Sibling',
  'Son',
  'Daughter',
  'Child',
]);

const SECOND_DEGREE_BASES: ReadonlySet<string> = new Set([
  'Grandfather',
  'Grandmother',
  'Grandparent',
  'Half-brother',
  'Half-sister',
  'Half-sibling',
  'Grandson',
  'Granddaughter',
  'Grandchild',
  'Uncle',
  'Aunt',
  'Uncle/Aunt',
  'Nephew',
  'Niece',
]);

export interface LetterTarget {
  readonly individualId: string;
  readonly displayName: string;
  readonly relationship: string;
}

export function selectAtRiskRelatives(register: RegisterData): LetterTarget[] {
  return register.rows
    .filter(row => isLetterTarget(row, register.probandId))
    .map(row => ({
      individualId: row.individualId,
      displayName: row.displayName,
      relationship: row.relationshipToProband,
    }));
}

function isLetterTarget(row: RegisterRow, probandId: string | null): boolean {
  if (row.individualId === probandId) {
    return false;
  }
  if (row.displayName.trim() === '') {
    return false;
  }
  return isFirstOrSecondDegree(row.relationshipToProband);
}

function isFirstOrSecondDegree(relationship: string): boolean {
  const base = stripSideSuffix(relationship).trim();
  if (base === '') {
    return false;
  }
  return FIRST_DEGREE_BASES.has(base) || SECOND_DEGREE_BASES.has(base);
}

function stripSideSuffix(relationship: string): string {
  for (const suffix of [' (maternal)', ' (paternal)']) {
    if (relationship.endsWith(suffix)) {
      return relationship.slice(0, -suffix.length);
    }
  }
  return relationship;
}
