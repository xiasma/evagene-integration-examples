/**
 * Validate a user-supplied regex before we store it.
 *
 * An EHR-specific patient-ID pattern is a foot-gun: a pattern like `\d+`
 * would mark every number on the page as a pedigree ID, injecting a
 * button next to every line-count and age. We reject patterns that match
 * short, unambiguous inputs (`123`, `abc`) to catch the obvious mistakes
 * without blocking legitimate short EHR identifiers of the form `ABC12345`.
 */

export type ValidationResult =
  | { readonly ok: true; readonly pattern: RegExp }
  | { readonly ok: false; readonly error: string };

const PROBE_STRINGS: readonly string[] = ['123', 'abc', '1', '42', 'hello'];

export function validatePattern(source: string): ValidationResult {
  const trimmed = source.trim();
  if (trimmed === '') {
    return { ok: false, error: 'Pattern must not be empty.' };
  }
  let pattern: RegExp;
  try {
    pattern = new RegExp(trimmed, 'g');
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, error: `Invalid regex: ${message}` };
  }
  const overmatch = PROBE_STRINGS.find(probe => pattern.test(probe));
  if (overmatch !== undefined) {
    return {
      ok: false,
      error: `Pattern is too loose — it matches '${overmatch}'. Anchor it (for example with \\b) or require more characters.`,
    };
  }
  return { ok: true, pattern };
}
