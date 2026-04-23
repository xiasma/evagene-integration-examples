# Shareable pedigree link

**Paste your pedigree ID and get an iframe snippet your family can read — without handing anyone a login.** The command mints a fresh read-only API key against your [Evagene](https://evagene.net) account, wraps the key into an `<iframe>` pointing at the embeddable viewer, and prints the whole HTML block to stdout. Drop it into a family-history website, a shared document, or an email, and relatives see the same pedigree you do — read-only, revocable, and scoped so it cannot modify anything.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree.

---

## Who this is for

- **Patients** who have built a family pedigree in Evagene and want to circulate it to relatives — aunts, uncles, grown children — for review or corroboration, without giving anyone account access.
- **Patient-portal integrators** building a "share with family" button on top of Evagene; this is the shape of the server call that sits behind it.
- **Developers** who want a short, clean example of the API-key creation endpoint and the embeddable-viewer URL shape.

## What Evagene surfaces this uses

- **REST API — API-key management** — `POST /api/auth/me/api-keys` to mint a new scoped key. The full plaintext key is returned once only.
- **Embeddable viewer** — `GET /api/embed/{pedigree_id}?api_key=...` serves a self-contained HTML page suitable as an `<iframe>` target.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and a **parent API key with `write` scope**, or a user JWT — see [getting-started.md](../getting-started.md). The parent key is the authority the demo uses to mint the new read-only key; it is *not* the key that ends up in the shared URL.
2. A pedigree you own, identified by its UUID. Find it in the Evagene web app URL bar (`https://evagene.net/pedigrees/<uuid>`).
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Both implementations read the same environment variables. Each language folder ships a `.env.example` you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` (the *parent* key — needs `write` scope) |

The pedigree ID and optional flags are passed on the command line, so you can share several pedigrees in one shell session without rewriting config.

## Command-line contract

Both implementations accept the same invocation:

```
shareable-link <pedigree-id> [--name <suffix>] [--label <human-label>]
```

- `pedigree-id` — UUID of the pedigree to share.
- `--name` — optional suffix for the minted key's name; defaults to a Unix timestamp. The full name is `share-<pedigree-id-prefix>-<suffix>`, so you can spot the key in *Account settings -> API keys* later.
- `--label` — optional human-readable iframe title (embedded in the `title="..."` attribute); defaults to `Family pedigree`.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Snippet printed |
| `64` | Usage error (missing or malformed arguments, missing `EVAGENE_API_KEY`) |
| `69` | Evagene API unreachable or returned a non-2xx response |

## Run it

Both implementations expect `EVAGENE_API_KEY` to be set in the environment, and the pedigree UUID as the first positional argument.

### Run it in Python 3.11+

```bash
cd python

# Create and activate a virtual environment
python -m venv .venv

# Windows (cmd / PowerShell):
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install the demo package + its dev tools (editable install so python -m <pkg> works)
pip install -e ".[dev]"

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m shareable_pedigree_link <pedigree-id>
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in Node 20+

```bash
cd node

# Install dependencies
npm install

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
npm start -- <pedigree-id>
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

## Expected output

A ready-to-paste HTML block, followed by a blank line and a one-line plaintext receipt of the key that was minted:

```
<!-- Evagene embeddable pedigree — read-only key minted 2026-04-20T12:00:00+00:00 -->
<iframe src="https://evagene.net/api/embed/a1cfe665-2e95-4386-9eb8-53d46095478a?api_key=evg_..." title="Family pedigree" width="100%" height="640" frameborder="0"></iframe>

Minted API key: evg_...   (stored only here — revoke at https://evagene.net/account/api-keys)
```

The `iframe` block is what you paste into your family site or email; the receipt line below it is for your own records — it is the *only* place the full key is ever shown. If you lose it, revoke the key at [https://evagene.net/account/api-keys](https://evagene.net/account/api-keys) and mint a new one.

## Architecture (identical in both languages)

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
                         EvageneClient ◄── HttpGateway (abstraction)
                                 │
                                 ▼
                        SnippetBuilder (pure)
                                 │
                                 ▼
                           Presenter (sink)
```

- **Config** — immutable value object; validates that `EVAGENE_API_KEY` is present and that the pedigree ID is a UUID.
- **HttpGateway** — narrow abstraction the tests fake.
- **EvageneClient** — two methods only: `create_read_only_api_key` (POSTs to `/api/auth/me/api-keys` with `scopes: ["read"]`) and `build_embed_url` (pure URL composition).
- **SnippetBuilder** — pure transform from minted key + label + embed URL to HTML, with attribute/text escaping.
- **Clock** and **KeyName** — tiny helpers, injected, so timestamps and key names are deterministic under test.
- **App** — composition root.

## Caveats

- **The minted key lives in the URL's query string.** Anyone with a copy of the iframe `src` can see the pedigree; the key has `read` scope only, but it is still a credential. Share the snippet over private channels (email, a password-protected family site). Do not paste it into a public GitHub gist, a public blog, or a page indexed by search engines.
- **Every invocation mints a new key.** If you run the command five times you will have five active keys, each of which works until revoked. Prune stale ones at [https://evagene.net/account/api-keys](https://evagene.net/account/api-keys) — Evagene caps you at 20 keys per account.
- **The minted key is never written anywhere except stdout.** The demo does not log it, does not save it to a file, and does not echo it to stderr. That is deliberate — if you wrap this demo in a shell pipeline, be careful not to log the whole stdout stream.
- **Read-only means read-only.** Relatives viewing the iframe cannot edit the pedigree, run risk calculations, or mint further keys. If a viewer needs write access they need their own Evagene account.
- This is an example integration, not a validated clinical tool. Clinical governance applies to any decision made from a shared pedigree.
