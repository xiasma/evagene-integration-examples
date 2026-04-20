/**
 * Static HTML views.  Keeping them in a typed module rather than a
 * template engine means the demo ships with zero extra runtime deps
 * and is still easy to read.
 */

const STYLE = `
  :root { --gap: 0.75rem; --accent: #0a58ca; --fg: #1f2937; }
  * { box-sizing: border-box; }
  body { font: 1rem/1.5 system-ui, sans-serif; color: var(--fg); max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  h1 { margin-top: 0; }
  fieldset { margin: 0 0 1.25rem; border: 1px solid #d1d5db; border-radius: 6px; padding: 1rem 1.25rem; }
  legend { font-weight: 600; padding: 0 0.5rem; }
  label { display: block; margin-bottom: var(--gap); }
  label span { display: block; font-size: 0.875rem; color: #4b5563; margin-bottom: 2px; }
  input, select { width: 100%; padding: 0.5rem 0.625rem; font: inherit; border: 1px solid #d1d5db; border-radius: 4px; }
  .row { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: var(--gap); align-items: end; }
  .row label { margin-bottom: 0; }
  button { background: var(--accent); color: white; border: 0; padding: 0.75rem 1.25rem; border-radius: 4px; font: inherit; cursor: pointer; }
  button:hover { filter: brightness(1.1); }
  .muted { color: #6b7280; font-size: 0.875rem; }
  .success, .error { padding: 1rem 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; }
  .success { background: #ecfdf5; border: 1px solid #10b981; }
  .error { background: #fef2f2; border: 1px solid #ef4444; }
  a { color: var(--accent); }
`.trim();

export function formPage(): string {
  return wrap(
    'Family-history intake',
    `
    <h1>Family-history intake</h1>
    <p class="muted">Fill in the family members you know about. Everything except the patient's name is optional; blanks are skipped.</p>

    <form method="post" action="/submit">
      <fieldset>
        <legend>Patient</legend>
        <label><span>Name (required)</span><input name="proband_name" required></label>
        <div class="row">
          <label><span>Biological sex</span>
            <select name="proband_sex">
              <option value="unknown">Prefer not to say</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </label>
          <label><span>Year of birth</span><input name="proband_year" type="number" min="1850" max="2030" inputmode="numeric"></label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Parents</legend>
        ${personRow('mother', 'Mother')}
        ${personRow('father', 'Father')}
      </fieldset>

      <fieldset>
        <legend>Maternal grandparents</legend>
        ${personRow('maternal_grandmother', 'Maternal grandmother')}
        ${personRow('maternal_grandfather', 'Maternal grandfather')}
      </fieldset>

      <fieldset>
        <legend>Paternal grandparents</legend>
        ${personRow('paternal_grandmother', 'Paternal grandmother')}
        ${personRow('paternal_grandfather', 'Paternal grandfather')}
      </fieldset>

      <fieldset>
        <legend>Siblings (optional, up to 4)</legend>
        ${siblingRow(0)}
        ${siblingRow(1)}
        ${siblingRow(2)}
        ${siblingRow(3)}
      </fieldset>

      <button type="submit">Create pedigree</button>
    </form>
    `,
  );
}

export function successPage(params: {
  readonly pedigreeId: string;
  readonly pedigreeUrl: string;
  readonly relativesAdded: number;
}): string {
  return wrap(
    'Pedigree created',
    `
    <div class="success">
      <h1>Pedigree created</h1>
      <p>Added the proband and <strong>${params.relativesAdded.toString()}</strong> relative(s).</p>
      <p>Pedigree ID: <code>${escapeHtml(params.pedigreeId)}</code></p>
      <p><a href="${escapeHtml(params.pedigreeUrl)}">Open in Evagene &rarr;</a></p>
    </div>
    <p><a href="/">Capture another family</a></p>
    `,
  );
}

export function errorPage(params: {
  readonly message: string;
  readonly partialPedigreeId?: string;
}): string {
  const partial =
    params.partialPedigreeId !== undefined
      ? `<p class="muted">A pedigree with ID <code>${escapeHtml(params.partialPedigreeId)}</code> was partially created; open it in Evagene to clean up or resume.</p>`
      : '';
  return wrap(
    'Something went wrong',
    `
    <div class="error">
      <h1>Something went wrong</h1>
      <p>${escapeHtml(params.message)}</p>
      ${partial}
    </div>
    <p><a href="/">Try again</a></p>
    `,
  );
}

function personRow(fieldPrefix: string, label: string): string {
  return `
    <div class="row">
      <label><span>${escapeHtml(label)} name</span><input name="${fieldPrefix}_name"></label>
      <label><span>Year of birth</span><input name="${fieldPrefix}_year" type="number" min="1850" max="2030" inputmode="numeric"></label>
      <span></span>
    </div>
  `.trim();
}

function siblingRow(index: number): string {
  return `
    <div class="row">
      <label><span>Name</span><input name="sibling_${index.toString()}_name"></label>
      <label><span>Relation</span>
        <select name="sibling_${index.toString()}_relation">
          <option value="">&mdash;</option>
          <option value="sister">Sister</option>
          <option value="brother">Brother</option>
          <option value="half_sister">Half sister</option>
          <option value="half_brother">Half brother</option>
        </select>
      </label>
      <label><span>Year of birth</span><input name="sibling_${index.toString()}_year" type="number" min="1850" max="2030" inputmode="numeric"></label>
    </div>
  `.trim();
}

function wrap(title: string, body: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>${STYLE}</style>
</head>
<body>
  <main>
    ${body.trim()}
  </main>
</body>
</html>`;
}

export function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
