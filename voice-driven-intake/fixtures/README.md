# Fixtures for voice-driven-intake

These files are deliberately synthetic. No patient data is included.

| File | Purpose | How it was produced |
|---|---|---|
| `sample-counselling.wav` | Placeholder 20-second mono 16 kHz PCM WAV alternating a quiet 220 Hz tone with silence. **Not a real dictation** -- it exercises the audio-loading and chunk-planning code paths without requiring a TTS install. Real smoke tests should use a short recording you make yourself. | Generated with Python's `wave` module (see `scripts/` section below). |
| `sample-transcript.txt` | Expected Whisper output for a short dictated family history. Used by the transcription-gateway fake in the test suite. Written to include typical speech disfluencies (filler words, a mid-sentence correction) to match what Whisper returns for real clinician speech. | Hand-written, synthetic family. |
| `sample-extraction.json` | Expected `ExtractedFamily` payload the LLM should return for `sample-transcript.txt`. Used by the LLM-gateway fake. | Hand-written to match the transcript. |

## Producing a real dictation fixture

If you want a realistic fixture, record 20 to 30 seconds of yourself reading `sample-transcript.txt` on a phone or laptop mic, save it as `my-dictation.m4a`, and point the CLI at it:

```
voice-intake fixtures/my-dictation.m4a --show-transcript
```

Do **not** commit that recording -- it is your own voice. The repository's `.gitignore` includes common audio extensions for this reason.

## Regenerating `sample-counselling.wav`

```python
import wave, struct, math
sr, dur = 16000, 20.0
with wave.open("sample-counselling.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    for i in range(int(sr * dur)):
        on = int(i / sr) % 2 == 0
        sample = int(5000 * math.sin(2 * math.pi * 220 * (i / sr))) if on else 0
        w.writeframesraw(struct.pack("<h", sample))
```
