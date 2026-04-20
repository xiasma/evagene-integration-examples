/**
 * Pure DOM side of the content script. The content-script entry point
 * wires this to `chrome.runtime.sendMessage` and `chrome.storage.local`
 * at runtime; tests drive it directly with a jsdom-provided `document`.
 */

export const MARKER_ATTRIBUTE = 'data-evagene-annotated';
export const BUTTON_CLASS = 'evagene-view-button';

export interface Annotator {
  readonly root: ParentNode;
  readonly pattern: RegExp;
  onClick(pedigreeId: string): void;
}

export function annotate(annotator: Annotator): number {
  const walker = textWalker(annotator.root);
  const candidates: Text[] = [];
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    candidates.push(node as Text);
  }
  let injected = 0;
  for (const node of candidates) {
    injected += annotateNode(node, annotator);
  }
  return injected;
}

function annotateNode(node: Text, annotator: Annotator): number {
  const parent = node.parentElement;
  if (parent === null) return 0;
  if (parent.closest(`[${MARKER_ATTRIBUTE}]`) !== null) return 0;
  const text = node.data;
  const matches = [...text.matchAll(withGlobal(annotator.pattern))];
  if (matches.length === 0) return 0;

  const doc = parent.ownerDocument;
  const fragment = doc.createDocumentFragment();
  const notify = (id: string): void => { annotator.onClick(id); };
  let cursor = 0;
  for (const match of matches) {
    const start = match.index;
    const end = start + match[0].length;
    if (start > cursor) {
      fragment.appendChild(doc.createTextNode(text.slice(cursor, start)));
    }
    fragment.appendChild(doc.createTextNode(text.slice(start, end)));
    fragment.appendChild(buildButton(doc, match[0], notify));
    cursor = end;
  }
  if (cursor < text.length) {
    fragment.appendChild(doc.createTextNode(text.slice(cursor)));
  }
  const wrapper = doc.createElement('span');
  wrapper.setAttribute(MARKER_ATTRIBUTE, 'true');
  wrapper.appendChild(fragment);
  node.replaceWith(wrapper);
  return matches.length;
}

function buildButton(
  doc: Document,
  pedigreeId: string,
  onClick: (id: string) => void,
): HTMLButtonElement {
  const button = doc.createElement('button');
  button.type = 'button';
  button.className = BUTTON_CLASS;
  button.textContent = 'View on Evagene';
  button.setAttribute('data-pedigree-id', pedigreeId);
  button.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    onClick(pedigreeId);
  });
  return button;
}

function textWalker(root: ParentNode): TreeWalker {
  const doc = (root as Node).ownerDocument ?? (root as Document);
  const filter = doc.defaultView?.NodeFilter ?? NodeFilter;
  return doc.createTreeWalker(root as Node, filter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = (node as Text).parentElement;
      if (parent === null) return filter.FILTER_REJECT;
      if (SKIP_TAGS.has(parent.tagName)) return filter.FILTER_REJECT;
      if (parent.closest(`[${MARKER_ATTRIBUTE}]`) !== null) {
        return filter.FILTER_REJECT;
      }
      return (node as Text).data.trim() === ''
        ? filter.FILTER_REJECT
        : filter.FILTER_ACCEPT;
    },
  });
}

const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'CODE', 'PRE']);

function withGlobal(pattern: RegExp): RegExp {
  return pattern.global ? pattern : new RegExp(pattern.source, `${pattern.flags}g`);
}
