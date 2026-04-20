# Getting started with Evagene integrations

This repository contains small, focused integration examples for [**Evagene**](https://evagene.net) — a clinical-grade pedigree drawing, management, and risk analysis platform. Each demo solves one concrete job for one type of user, and is shipped in several languages so you can copy the version that matches your stack.

This document covers the one-time setup every demo expects: how to register, get an API key, and point the code at the Evagene service. Work through it once — every demo after that is a short `README.md` and a `run` command.

---

## 1. Register for Evagene

1. Go to **[https://evagene.net](https://evagene.net)** and create an account.
2. Evagene is currently invite-only — you may need to be approved by the Evagene team before your account becomes active. Sign up and watch for the confirmation email.
3. Sign in. The canvas opens — that is the Evagene pedigree editor.

You do not need any special licence or plan to use the integration API. If you can sign in to the web app, you can call the API.

## 2. Create an API key

Integration demos authenticate with a long-lived **API key**, not your password. Keys are scoped so you can give a demo the narrowest permission it needs and revoke it at any time without disturbing your login.

1. Sign in at [https://evagene.net](https://evagene.net).
2. Open **Account settings → API keys**.
3. Click **Generate a new key** and give it a name that will remind you why it exists (e.g. `nice-traffic-light (laptop)`).
4. Choose the scopes. Most demos in this repo need either:
   - **`read`** — list and fetch pedigrees, individuals, diseases (no writes).
   - **`analyze`** — run risk calculations and AI interpretations.
   - **`write`** — create or mutate pedigree data (only a few demos need this).
5. **Copy the full key immediately.** It starts with `evg_` and is shown **once**. Evagene only stores a hash — if you lose it, you delete and regenerate.
6. Paste it into the demo's `.env` file as `EVAGENE_API_KEY` (see `.env.example` in every demo folder for the exact variable name).

**Never commit an API key.** The repository's `.gitignore` blocks `.env`, but double-check any config you write before you push.

## 3. Point the code at Evagene

Every demo reads two environment variables:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | Only override if your organisation hosts Evagene at a different URL. |
| `EVAGENE_API_KEY`  | yes | — | The `evg_...` key you created in step 2. |

Each demo folder ships a `.env.example` (or `.Renviron.example` for R) listing exactly the variables it needs. Copy it to `.env` and fill in the values.

## 4. Have a pedigree to work on

Most demos operate on a specific pedigree and ask for a **pedigree ID** on the command line. You can find the ID in two places:

- The URL bar when you have the pedigree open in the Evagene web app — it looks like `https://evagene.net/pedigrees/7c8d4d6a-...`. The UUID is the ID.
- The `GET /api/pedigrees` endpoint, which returns a list of pedigrees you own.

**If you don't yet have a pedigree to try the demos against**, build one in Evagene first. The homepage has an import option for `.ged` (GEDCOM), `.xeg`, and `.json` files — or you can draw one by hand in a few minutes. For the breast-cancer-focused demos, anything with a mother or sister affected by breast cancer will exercise the NICE and Tyrer-Cuzick code paths meaningfully.

## 5. Rate limits and etiquette

API keys have configurable per-minute and per-day rate limits. Defaults are generous for interactive use but demos that fan out across an archive (bulk imports, batch risk screening) should:

- Space calls out — handle HTTP 429 responses with a backoff rather than retrying in a tight loop.
- Use the narrowest scope that works — a read-only batch screener does not need a `write` key.
- Revoke keys when you no longer need them. You can always generate a fresh one.

## 6. Where to get help

- **Interactive API reference** — [`https://evagene.net/docs`](https://evagene.net/docs) (Swagger UI) and [`https://evagene.net/redoc`](https://evagene.net/redoc). Every endpoint, every field.
- **Product documentation** — linked from the Evagene web app footer.
- **Issues with this repository** — open a GitHub issue against the repo.

---

## What this repository is not

These are **example integrations**, not validated clinical tools. They illustrate how to talk to Evagene from each language. Any decision made in a clinical context must go through the usual clinical governance — read the Evagene product disclaimers for the full picture. The risk-model caveats (Tyrer-Cuzick is an IBIS-style approximation; BOADICEA is not bundled but exported to canrisk.org) apply here too.
