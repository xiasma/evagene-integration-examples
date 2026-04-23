# Voice-driven intake

**Hold the mic, talk through a family history for a minute, and get a structured pedigree ready to review in [Evagene](https://evagene.net) -- single-handed, no typing.**

The tool reads an audio recording (`.wav`, `.m4a`, `.mp3`, `.webm`, `.ogg`), transcribes it with OpenAI Whisper using your own API key, asks Claude (also your own key) to pull out the proband and relatives, and prints the result as pretty JSON plus a human-readable preview. With `--commit`, it then uses the Evagene REST API to create the pedigree and wire the relatives up.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** -- it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **Genetic counsellors** who prefer dictation to typing. Record the patient visit (or dictate after), review the extracted structure, commit when happy.
- **Mobile / visiting clinicians** capturing a family history single-handed -- phone in one hand, kettle in the other -- between home visits.
- **Integrators** wanting a short, auditable example of a BYOK two-provider pipeline (Whisper + Claude) that keeps the recording and the raw transcript out of Evagene's infrastructure.

## Which Evagene surfaces this uses

- **BYOK LLM (user side)** -- audio goes directly to OpenAI using your `OPENAI_API_KEY`; the transcript then goes directly to Anthropic using your `ANTHROPIC_API_KEY`. Neither passes through Evagene.
- **REST API** -- when `--commit` is set: `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{ind_id}`, `PATCH /api/individuals/{id}` (proband), `POST /api/pedigrees/{id}/register/add-relative`.
- **Authentication** -- `X-API-Key: evg_...` with `write` scope (only needed for `--commit`).
- **Interactive API reference** -- [https://evagene.net/docs](https://evagene.net/docs).

### Privacy architecture

```
  audio recording  ──►  this CLI  ──►  OpenAI Whisper
                                       (your OPENAI_API_KEY)
                           │
                           │  plain-text transcript (in-memory only)
                           ▼
                        Anthropic (Claude)
                        (your ANTHROPIC_API_KEY)
                           │
                           │  extracted structured family
                           ▼
                        Evagene REST (only with --commit)
                        (your EVAGENE_API_KEY)
```

The pipeline sees two distinct vendors. Confirm that **both** your OpenAI and Anthropic data-handling terms (zero-retention / enterprise / BAA, as applicable) are acceptable for your clinical context before running real recordings through this. Evagene never sees the audio or the transcript -- only the extracted structured family, and only when you pass `--commit`.

The tool never writes the audio or the transcript to disk except in two explicit places: the temporary chunk slices created by ``pydub`` when a long recording is cut at silence boundaries (deleted when the run finishes), and the transcript printed to stdout when you pass `--show-transcript`. It never logs either.

## Prerequisites

1. An **OpenAI API key** -- [platform.openai.com](https://platform.openai.com/api-keys). Export it as `OPENAI_API_KEY`.
2. An **Anthropic API key** -- [console.anthropic.com](https://console.anthropic.com). Export it as `ANTHROPIC_API_KEY`.
3. An **Evagene account and API key** with `write` scope for `--commit` -- see [../getting-started.md](../getting-started.md).
4. **ffmpeg on your PATH** -- pydub uses it to decode non-WAV formats and to slice long recordings. Install via your OS package manager (`brew install ffmpeg`, `apt install ffmpeg`, winget / choco on Windows).
5. Python **3.11+**.

## Configuration

Each language folder ships a `.env.example`. Copy to `.env` and fill in.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | -- | Starts with `sk-...`. Used for Whisper. |
| `ANTHROPIC_API_KEY` | yes (except `--show-prompt` / `--show-transcript`) | -- | Starts with `sk-ant-...`. Used for extraction. |
| `EVAGENE_BASE_URL`  | no | `https://evagene.net` | Override only if your organisation hosts Evagene elsewhere. |
| `EVAGENE_API_KEY`   | only with `--commit` | -- | `write` scope. Starts with `evg_...`. |
| `VOICE_INTAKE_MAX_DURATION_S` | no | `1800` (30 min) | Hard cap on recording length; longer audio is rejected with exit 71. |

The tool never logs any of these, nor the audio, nor the transcript.

## Command-line contract

```
voice-intake <audio-file> [--commit] [--language <ISO>] [--show-transcript] [--show-prompt] [--model <claude-model>]
```

- `<audio-file>` -- positional path to the recording. Required unless `--show-prompt` is set.
- `--commit` -- after extraction, create the pedigree in Evagene (requires `EVAGENE_API_KEY`).
- `--language <ISO>` -- Whisper language hint (ISO-639-1, e.g. `en`). Omit for auto-detect.
- `--show-transcript` -- transcribe and print the transcript only, then exit. Useful for QA-ing the speech layer separately from the LLM layer.
- `--show-prompt` -- print the system prompt and JSON schema that would be sent to Anthropic and exit. No network calls.
- `--model <claude-model>` -- override the default Claude model (`claude-sonnet-4-6`).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `64` | Usage / configuration error |
| `69` | OpenAI, Anthropic, or Evagene unreachable |
| `70` | Model output did not conform to the extraction schema |
| `71` | Audio file missing, wrong format, too large, or longer than the duration cap |

## Run it

Only a Python implementation ships: the pipeline depends on `pydub`, the OpenAI Whisper SDK, and the Anthropic SDK, and duplicating it in another language would not add anything.

The sample WAV in `fixtures/` is a **synthetic placeholder** (tones and silence, produced by a short Python script -- see `fixtures/README.md`). For a realistic run, record yourself reading `fixtures/sample-transcript.txt` into a phone or laptop mic and save it as `fixtures/my-dictation.m4a`. The demo's `.gitignore` blocks audio files by default so you cannot accidentally commit your voice.

### Run it in Python 3.11+

**System prerequisite:** install **ffmpeg** and make sure it is on `PATH` — `pydub` (audio loading) and the OpenAI Whisper API audio-upload path both depend on it. Windows: `choco install ffmpeg` or download from <https://ffmpeg.org/download.html>. macOS: `brew install ffmpeg`. Linux: `apt-get install ffmpeg` / `dnf install ffmpeg`.

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

# Set your API keys (one shell session)
# Windows PowerShell:
$env:OPENAI_API_KEY = "sk-..."
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export EVAGENE_API_KEY=evg_...

# Transcribe and print the transcript only
python -m voice_driven_intake ../fixtures/sample-counselling.wav --show-transcript

# Extract the family structure
python -m voice_driven_intake ../fixtures/sample-counselling.wav

# Extract and commit to Evagene
python -m voice_driven_intake ../fixtures/sample-counselling.wav --commit
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

## Expected output

With `--show-transcript`, stdout is the Whisper transcript followed by a newline. That is all.

Without `--show-transcript` or `--commit`, stdout is a pretty-printed JSON block matching the schema plus a readable preview:

```json
{
  "proband": { "display_name": "Emma Carter", "biological_sex": "female", "year_of_birth": 1985, "notes": null },
  ...
}
```

```
Extracted family
  proband  Emma Carter (female, b.1985)
  mother   Grace (b.1957) -- Aged 68, no cancers.
  ...
```

With `--commit`, two extra lines appear at the end:

```
Created pedigree 7c8d4d6a-...-...
https://evagene.net/pedigrees/7c8d4d6a-...-...
```

## Architecture

```
  audio file (.wav/.m4a/.mp3/.webm/.ogg)
        │
        ▼
   AudioSource                 ─ path, format, size validation
        │
        ▼
   WhisperTranscriber ──► AudioProbe       (pydub-backed: duration + silence detection)
        │              ──► Chunker         (pure: silence-midpoint chunk planning)
        │              ──► TranscriptionGateway  (OpenAI Whisper: one request per chunk)
        ▼
   transcript (string, in-memory)
        │
        ▼
   TextExtractor ──► LlmGateway (Anthropic SDK with tool-use schema)
        │
        ▼
   ExtractedFamily (value object)
        │
        ├─►  Presenter      (always)
        │       pretty JSON + human-readable preview
        │
        └─►  EvageneWriter  (only with --commit)
                   │
                   ├─► EvageneClient.createPedigree
                   ├─► EvageneClient.createIndividual      (proband)
                   ├─► EvageneClient.addIndividualToPedigree
                   ├─► EvageneClient.designateAsProband
                   └─► EvageneClient.addRelative           (per relative, in order)
                                     │
                                     ▼
                              HttpGateway (abstraction)
```

Every module has one responsibility. The `AudioProbe`, `TranscriptionGateway`, `LlmGateway`, and `HttpGateway` abstractions mean the tests can run the whole flow end-to-end without touching OpenAI, Anthropic, or the network. Audio longer than ~20 minutes is split at silence midpoints before transcription so each request stays under Whisper's 25 MB per-request ceiling.

## Caveats

- **Always review before `--commit`.** Two LLMs run in series (speech-to-text, then structured extraction). Either one can get a name or an age wrong. Run once read-only, eyeball the JSON and preview, fix the transcript or re-run before committing to Evagene.
- **Audio and transcripts may contain PHI.** The audio is sent to OpenAI; the transcript is sent to Anthropic. Two sets of data-handling terms apply. Confirm both policies (zero-retention add-ons, enterprise agreements, BAAs) suit your clinical context before passing real patient material.
- **ffmpeg is required.** `pydub` reads non-WAV formats and slices long recordings via `ffmpeg`. If it is not on your PATH, the tool will fail with a clear error on any `.m4a` / `.mp3` / `.webm` input.
- **Duration cap defaults to 30 minutes.** Raise with `VOICE_INTAKE_MAX_DURATION_S` if you really need to push a long consultation through -- and expect transcription cost and latency to scale with length.
- **The sample `.wav` in `fixtures/` is synthetic** (tones and silence). It exercises the audio-loading and chunk-planning code paths but does not contain real speech; Whisper will return roughly nothing for it. Record your own short dictation to see an end-to-end run.
- **Diseases and conditions are captured as free-text `notes`, not coded.** The schema keeps proband / parents / grandparents / siblings structured; disease diagnoses mentioned in the transcript are preserved in a per-relative `notes` field so a clinician can read them, but they are not translated into Evagene's structured disease codes. That is intentional -- getting structured disease coding wrong silently is worse than leaving it to the clinician.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
