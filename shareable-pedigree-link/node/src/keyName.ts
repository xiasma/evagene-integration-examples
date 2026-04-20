const PEDIGREE_ID_PREFIX_LENGTH = 8;

export interface KeyNameRequest {
  readonly pedigreeId: string;
  readonly suffix: string;
}

export function buildKeyName(request: KeyNameRequest): string {
  const prefix = request.pedigreeId.slice(0, PEDIGREE_ID_PREFIX_LENGTH);
  return `share-${prefix}-${request.suffix}`;
}
