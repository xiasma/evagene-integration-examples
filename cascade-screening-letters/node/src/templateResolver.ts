/**
 * Find or create the cascade-screening analysis template.
 *
 * If the caller passed `--template <id>` we trust it. Otherwise we look for
 * an existing template by name and, failing that, create one seeded with
 * the conservative default body below.
 */

import type { EvageneApi } from './evageneClient.js';

export const DEFAULT_TEMPLATE_NAME = 'cascade-screening-letter';

const DEFAULT_TEMPLATE_DESCRIPTION =
  'Evagene integration example. Conservative first-draft body for a cascade-screening ' +
  'invitation letter. Counsellor review before sending is mandatory.';

export const DEFAULT_TEMPLATE_BODY = `\
Write a short, conservative cascade-screening invitation letter body (three \
paragraphs, British English, plain prose, no bullet points, no clinical jargon). \
Address it to a relative of the proband. The letter must:

- State that a genetic result has been identified in the family of \
{{proband_name}}, without naming the specific variant;
- Note the condition(s) being discussed in the family: {{disease_list}};
- Reference the risk context where relevant: {{risk_summary}};
- Invite the reader to consider speaking with their genetic counsellor about \
whether the identified variant is relevant to them, and about any surveillance \
or preventative options that would follow;
- Make clear there is no obligation to act and that the reader may take as much \
time as they need;
- Avoid prescriptive language ("you must", "you should"); prefer permissive \
phrasing ("you may wish to consider", "you are welcome to").

Do not include a salutation, a sign-off, or any contact details — the \
counsellor will add those to match their clinic's letterhead. Return only the \
three paragraphs of letter body.
`;

export async function resolveTemplateId(
  client: EvageneApi,
  override: string | undefined,
  name: string = DEFAULT_TEMPLATE_NAME,
): Promise<string> {
  if (override !== undefined) {
    return override;
  }
  const existing = await client.listTemplates();
  const match = existing.find(template => template.name === name);
  if (match !== undefined) {
    return match.id;
  }
  const created = await client.createTemplate({
    name,
    description: DEFAULT_TEMPLATE_DESCRIPTION,
    userPromptTemplate: DEFAULT_TEMPLATE_BODY,
  });
  return created.id;
}
