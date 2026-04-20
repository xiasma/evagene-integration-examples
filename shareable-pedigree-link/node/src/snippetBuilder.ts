export interface SnippetRequest {
  readonly embedUrl: string;
  readonly label: string;
  readonly mintedAt: string;
  readonly plaintextKey: string;
  readonly revokeUrl: string;
}

const IFRAME_HEIGHT_PX = 640;

export function buildSnippet(request: SnippetRequest): string {
  const src = escapeAttribute(request.embedUrl);
  const title = escapeAttribute(request.label);
  const mintedAt = escapeHtml(request.mintedAt);
  return (
    `<!-- Evagene embeddable pedigree \u2014 read-only key minted ${mintedAt} -->\n` +
    `<iframe src="${src}" title="${title}" width="100%" height="${IFRAME_HEIGHT_PX.toString()}" frameborder="0"></iframe>\n` +
    `\n` +
    `Minted API key: ${request.plaintextKey}   ` +
    `(stored only here \u2014 revoke at ${request.revokeUrl})\n`
  );
}

const ATTRIBUTE_ESCAPES: ReadonlyMap<string, string> = new Map([
  ['&', '&amp;'],
  ['<', '&lt;'],
  ['>', '&gt;'],
  ['"', '&quot;'],
]);

const HTML_ESCAPES: ReadonlyMap<string, string> = new Map([
  ['&', '&amp;'],
  ['<', '&lt;'],
  ['>', '&gt;'],
]);

function escapeAttribute(value: string): string {
  return replaceFrom(value, ATTRIBUTE_ESCAPES);
}

function escapeHtml(value: string): string {
  return replaceFrom(value, HTML_ESCAPES);
}

function replaceFrom(value: string, table: ReadonlyMap<string, string>): string {
  let result = '';
  for (const char of value) {
    result += table.get(char) ?? char;
  }
  return result;
}
