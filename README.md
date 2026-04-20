# Evagene integration examples

Small, focused examples showing how to integrate with [**Evagene**](https://evagene.net) — a clinical-grade pedigree drawing, management, and risk analysis platform. Each demo solves one concrete job for one type of user, and ships in the languages that make sense for it. **Python**, **Node.js / TypeScript**, **.NET (C#)**, **R**, and **Go** are all represented.

If you've ever wanted to hook a family-history intake form, a clinic webhook listener, a research risk calculator, an AI agent, a Slack bot, an EHR browser extension, or a teaching notebook up to Evagene — start here.

## Start here

**[getting-started.md](./getting-started.md)** — register at [evagene.net](https://evagene.net), mint an API key, configure `EVAGENE_API_KEY` and `EVAGENE_BASE_URL`. One read, then every demo below is a `README.md` and a `run` command.

## The demos

### Point of care — intake and triage

| Demo | What it does | Languages |
|---|---|---|
| [nice-traffic-light](./nice-traffic-light/) | One command → NICE CG164 / NG101 breast-cancer triage as `GREEN` / `AMBER` / `RED` plus the exact triggers matched | Python · Node · .NET · R |
| [family-history-intake-form](./family-history-intake-form/) | Web form that captures three generations of family history and creates a fully-structured pedigree via REST | Python · Node · .NET |
| [chat-bot](./chat-bot/) | Slack and Teams bot: `/evagene show <id>` → pedigree name, proband, NICE category, SVG thumbnail | Node |

### Clinical-geneticist tooling

| Demo | What it does | Languages |
|---|---|---|
| [canrisk-bridge](./canrisk-bridge/) | Hand off a pedigree to BOADICEA / [canrisk.org](https://canrisk.org) in one command — fetch the `##CanRisk 2.0` export, save it, optionally open the browser | Python · Node · .NET · R |
| [archive-triage-runner](./archive-triage-runner/) | Point at a folder of GEDCOMs; get a CSV flagging every family by NICE category, ready to sort | Python · .NET |
| [bayesmendel-comparator](./bayesmendel-comparator/) | Same pedigree, three BayesMendel models (BRCAPRO / MMRpro / PancPRO), one side-by-side comparison table | R · Python |
| [tumour-board-briefing](./tumour-board-briefing/) | One-command PDF for MDT meetings — Claus, Couch, Frank, Manchester, NICE, Tyrer-Cuzick, plus boilerplate caveats, cover page, and a pedigree figure | Python |
| [cascade-screening-letters](./cascade-screening-letters/) | Given a proband, generate a personalised draft letter for each at-risk relative using an Evagene analysis template | Python · Node |
| [pedigree-diff](./pedigree-diff/) | Compare two pedigrees (or snapshots of the same pedigree at different times); produce a readable text / JSON / Markdown changelog | Python |

### Reproductive medicine

| Demo | What it does | Languages |
|---|---|---|
| [couple-carrier-risk](./couple-carrier-risk/) | Two 23andMe raw exports → combined per-disease carrier frequency and couple-offspring-risk table, AR + XLR diseases | Python · R |

### Research

| Demo | What it does | Languages |
|---|---|---|
| [publication-figure-renderer](./publication-figure-renderer/) | Print-quality SVG ready for publication, with optional de-identification (generation-number labels `I-1`, `II-3`, etc.) | R · Python |
| [research-cohort-anonymiser](./research-cohort-anonymiser/) | Strip direct identifiers, preserve structure, estimate k-anonymity — research-safe pedigrees you can share | Python · R |
| [notebook-explorer](./notebook-explorer/) | Jupyter (Python) and Quarto (R) notebooks: interactive what-if risk exploration — vary penetrance, parity, heritability, watch TC / NICE / multifactorial move | Python · R |

### AI agents and multimodal input

| Demo | What it does | Languages |
|---|---|---|
| [mcp-server](./mcp-server/) | Model Context Protocol server exposing Evagene to Claude Desktop / Cursor / any MCP client — list, inspect, add, calculate | Python · Node · Go |
| [call-notes-to-pedigree](./call-notes-to-pedigree/) | Paste a counselling transcript; the user's own Claude extracts a structured pedigree; `--commit` persists it to Evagene | Python · Node |
| [pedigree-ocr](./pedigree-ocr/) | Photo of a hand-drawn pedigree → structured Evagene pedigree via Claude Vision; `--commit` to persist | Python |
| [voice-driven-intake](./voice-driven-intake/) | Audio of a counselling session → Whisper transcript → Claude extraction → structured pedigree | Python |

### Integration and workflow

| Demo | What it does | Languages |
|---|---|---|
| [fhir-bridge](./fhir-bridge/) | Two-way sync between Evagene pedigrees and FHIR R5 `FamilyMemberHistory` Bundles; push a pedigree to a FHIR server, pull a FHIR patient in | Node · .NET |
| [webhook-audit-blotter](./webhook-audit-blotter/) | HMAC-verified webhook receiver that writes a tamper-evident SQLite log with a hash-chained schema | Node · .NET · Python |
| [clinic-referral-dashboard](./clinic-referral-dashboard/) | Live clinic dashboard — webhook-verified events + Server-Sent Events + embedded pedigree cards with NICE category | Node |
| [longitudinal-risk-monitor](./longitudinal-risk-monitor/) | Scheduled job (cron / systemd / GitHub Actions) that alerts Slack / stdout / file when any pedigree's NICE category changes | Python |
| [xeg-upgrader](./xeg-upgrader/) | Legacy Evagene v1 `.xeg` XML → current pedigree; parse-preview or create | .NET · Python |
| [shareable-pedigree-link](./shareable-pedigree-link/) | Mint a scoped read-only API key and return an `<iframe>`-ready embed URL the patient can share with relatives | Node · Python |
| [browser-extension](./browser-extension/) | Manifest V3 cross-browser extension — highlights patient UUIDs on any page, pops the pedigree in a side panel | Node (WebExtensions) |

### Teaching

| Demo | What it does | Languages |
|---|---|---|
| [pedigree-puzzle-generator](./pedigree-puzzle-generator/) | Generate random inheritance-pattern quizzes (AD / AR / XLR / XLD / MT) with answer keys — classroom-ready | Python · Node |

Each demo's folder has its own `README.md` with a value-first explanation, prerequisites, environment variables, a one-line run command per language, and the architecture at a glance.

## Which demo should I look at first?

- **You want to see Evagene's REST API in action, end-to-end:** [nice-traffic-light](./nice-traffic-light/). It's the smallest, and every other demo reuses its architecture.
- **You're building a clinical web form that creates pedigrees:** [family-history-intake-form](./family-history-intake-form/).
- **You want Evagene inside your team's Slack or Teams:** [chat-bot](./chat-bot/).
- **You're wiring Evagene into hospital EHR / records infrastructure:** [webhook-audit-blotter](./webhook-audit-blotter/), [clinic-referral-dashboard](./clinic-referral-dashboard/), and [fhir-bridge](./fhir-bridge/).
- **You're doing research or cohort work:** [archive-triage-runner](./archive-triage-runner/), [bayesmendel-comparator](./bayesmendel-comparator/), [research-cohort-anonymiser](./research-cohort-anonymiser/), [notebook-explorer](./notebook-explorer/).
- **You want an AI assistant that can read and mutate pedigrees:** [mcp-server](./mcp-server/) plus [call-notes-to-pedigree](./call-notes-to-pedigree/) / [pedigree-ocr](./pedigree-ocr/) / [voice-driven-intake](./voice-driven-intake/).
- **You're teaching genetics:** [pedigree-puzzle-generator](./pedigree-puzzle-generator/) and [notebook-explorer](./notebook-explorer/).
- **You're preparing a publication figure:** [publication-figure-renderer](./publication-figure-renderer/).

## House style

Every demo in this repo:

- Leads its README with **user value**, not API trivia.
- Targets a **recent runtime** with **pinned dependencies**, so it doesn't rot when a transitive dep bumps.
- Splits code along **Single Responsibility** lines (config, HTTP gateway, API client, domain logic, presenter, composition root) — the same shape across every language so reading one helps you read the others.
- Ships **unit tests**, **lint-clean source**, and **strict type-checking** per language. Across the repo that's over **1,400 tests**.
- **Smoke-tests live against `https://evagene.net`** during development — most demos create and then delete their own scratch data so your account stays tidy.
- Reads secrets from **environment variables**, never from code. An `.env.example` in every language folder lists exactly what's needed.

## Integration surfaces

Evagene exposes several integration mechanisms; these demos collectively cover them:

- **REST API** — CRUD, risk calculation, import/export, analysis templates. Every demo touches this.
- **Webhooks** — HMAC-signed push notifications (`X-Evagene-Signature-256: sha256=...`) for pedigree + individual + analysis events. See [webhook-audit-blotter](./webhook-audit-blotter/) and [clinic-referral-dashboard](./clinic-referral-dashboard/).
- **MCP server** — stdio-based agent tool API. See [mcp-server](./mcp-server/).
- **Analysis templates** — reusable LLM prompt templates with variable injection. See [cascade-screening-letters](./cascade-screening-letters/).
- **BYOK LLM** — route AI interpretation through a user-supplied Anthropic / OpenAI key. See [call-notes-to-pedigree](./call-notes-to-pedigree/), [pedigree-ocr](./pedigree-ocr/), [voice-driven-intake](./voice-driven-intake/).
- **Embeddable viewer** — SVG / HTML widget for third-party sites. See [shareable-pedigree-link](./shareable-pedigree-link/), [clinic-referral-dashboard](./clinic-referral-dashboard/), [browser-extension](./browser-extension/).
- **File formats** — GEDCOM 5.5.1 · `.xeg` · 23andMe · CanRisk v2 · FHIR R5. See [canrisk-bridge](./canrisk-bridge/), [archive-triage-runner](./archive-triage-runner/), [xeg-upgrader](./xeg-upgrader/), [fhir-bridge](./fhir-bridge/), [couple-carrier-risk](./couple-carrier-risk/).
- **R sidecar** — BayesMendel cancer-risk models (BRCAPRO, MMRpro, PancPRO) served via the main REST API. See [bayesmendel-comparator](./bayesmendel-comparator/).
- **SVG export** — print-quality figures. See [publication-figure-renderer](./publication-figure-renderer/), [tumour-board-briefing](./tumour-board-briefing/).

Authoritative endpoint reference: **[https://evagene.net/docs](https://evagene.net/docs)** (Swagger) and **[https://evagene.net/redoc](https://evagene.net/redoc)**.

## Licence

[MIT](./LICENSE). Copy, adapt, and build on these demos with no strings attached — just keep the copyright notice.

## Caveats

These are **example integrations**, not validated clinical tools. Any use in a clinical context must go through the usual clinical-governance process.

Risk-model caveats apply as they do on the Evagene product itself:

- **Tyrer-Cuzick** is an IBIS-style approximation of the 2004 algorithm, not the official IBIS binary.
- **BOADICEA is not bundled** — Evagene exports a `##CanRisk 2.0` pedigree file that the clinician uploads at [canrisk.org](https://canrisk.org) for the full BOADICEA assessment.
- **BayesMendel models** (BRCAPRO, MMRpro, PancPRO) return mutation carrier probabilities, not deterministic diagnoses. Cite Parmigiani / Chen / Wang as appropriate.
- **LLM-driven demos** (call-notes, pedigree-ocr, voice-driven-intake) are extraction aids, not authoritative clinical tools — always review the structured output before committing.
