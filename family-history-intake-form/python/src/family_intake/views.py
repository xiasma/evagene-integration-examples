"""Static HTML views.  No templating engine on purpose -- this demo is
about the Evagene integration, not Jinja."""

from __future__ import annotations

from html import escape as _escape

_STYLE = """
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
""".strip()


def form_page() -> str:
    body = f"""
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
        {_person_row("mother", "Mother")}
        {_person_row("father", "Father")}
      </fieldset>

      <fieldset>
        <legend>Maternal grandparents</legend>
        {_person_row("maternal_grandmother", "Maternal grandmother")}
        {_person_row("maternal_grandfather", "Maternal grandfather")}
      </fieldset>

      <fieldset>
        <legend>Paternal grandparents</legend>
        {_person_row("paternal_grandmother", "Paternal grandmother")}
        {_person_row("paternal_grandfather", "Paternal grandfather")}
      </fieldset>

      <fieldset>
        <legend>Siblings (optional, up to 4)</legend>
        {_sibling_row(0)}
        {_sibling_row(1)}
        {_sibling_row(2)}
        {_sibling_row(3)}
      </fieldset>

      <button type="submit">Create pedigree</button>
    </form>
    """
    return _wrap("Family-history intake", body)


def success_page(*, pedigree_id: str, pedigree_url: str, relatives_added: int) -> str:
    body = f"""
    <div class="success">
      <h1>Pedigree created</h1>
      <p>Added the proband and <strong>{relatives_added}</strong> relative(s).</p>
      <p>Pedigree ID: <code>{_escape(pedigree_id)}</code></p>
      <p><a href="{_escape(pedigree_url)}">Open in Evagene &rarr;</a></p>
    </div>
    <p><a href="/">Capture another family</a></p>
    """
    return _wrap("Pedigree created", body)


def error_page(*, message: str, partial_pedigree_id: str | None = None) -> str:
    partial = ""
    if partial_pedigree_id is not None:
        partial = (
            f'<p class="muted">A pedigree with ID <code>{_escape(partial_pedigree_id)}</code> '
            "was partially created; open it in Evagene to clean up or resume.</p>"
        )
    body = f"""
    <div class="error">
      <h1>Something went wrong</h1>
      <p>{_escape(message)}</p>
      {partial}
    </div>
    <p><a href="/">Try again</a></p>
    """
    return _wrap("Something went wrong", body)


def _person_row(field_prefix: str, label: str) -> str:
    return f"""
    <div class="row">
      <label><span>{_escape(label)} name</span><input name="{field_prefix}_name"></label>
      <label><span>Year of birth</span><input name="{field_prefix}_year" type="number" min="1850" max="2030" inputmode="numeric"></label>
      <span></span>
    </div>
    """.strip()


def _sibling_row(index: int) -> str:
    return f"""
    <div class="row">
      <label><span>Name</span><input name="sibling_{index}_name"></label>
      <label><span>Relation</span>
        <select name="sibling_{index}_relation">
          <option value="">&mdash;</option>
          <option value="sister">Sister</option>
          <option value="brother">Brother</option>
          <option value="half_sister">Half sister</option>
          <option value="half_brother">Half brother</option>
        </select>
      </label>
      <label><span>Year of birth</span><input name="sibling_{index}_year" type="number" min="1850" max="2030" inputmode="numeric"></label>
    </div>
    """.strip()


def _wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{_escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>{_STYLE}</style>
</head>
<body>
  <main>
    {body.strip()}
  </main>
</body>
</html>"""
