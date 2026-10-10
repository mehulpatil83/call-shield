# call-shield

A privacy-conscious voice-scam and audio-authenticity checker for English, Hinglish and Marathi calls, built for the
Great Indian AI Internship Challenge by Gnani.ai. Inspired by Panopticon (University of Peradeniya, AURORA AI
IDEATHON 2026). This is an independent implementation: no Panopticon code is used.

**Status:** Phase 0 (smoke tests) and Phase 1 (core engine) are done. The FastAPI and React app is next.

## What it does
1. Transcribes a consented recording with Gnani STT in English, Hinglish or Marathi (results cached on disk).
2. Checks the conversation for social-engineering tactics with an explainable, rule-based engine: every alert
   quotes the transcript.
3. Separately estimates whether the audio sounds synthetic with a pretrained anti-spoofing model (AASIST-L, CPU only).
4. Shows the two findings side by side, with uncertainty and limitations.

The two checks are deliberately independent: a real person can run a scam, and a synthetic voice can say
something harmless.

## Quick start (Windows, CPU only)
```
pip install -r requirements-core.txt
python -m pytest tests -q
python -m core.analyse --text phase0\audio\hinglish_scam.txt --lang hinglish
python -m core.analyse phase0\audio\en_scam.wav
```
Put your Gnani key in `.env` (copy `phase0\.env.example`): `GNANI_API_KEY=...`.
Reports are written to `reports\` (open the `.html` file). More detail: `core\README.md`.

## Repo layout
- `core/` the analysis engine (Gnani cache, rules, authenticity, report)
- `tests/` automated tests (fake Gnani and fake model, so they cost nothing)
- `phase0/` smoke tests for Gnani STT and the anti-spoofing model on a CPU-only machine
- `app/` (coming) FastAPI backend and React/TypeScript frontend

## Privacy
Audio is sent to Gnani's API for transcription, so recordings need the speakers' consent. Recordings, transcripts,
reports, API keys and model files are never committed to this repository.

## Limitations (honest summary so far)
- The anti-spoofing model is weak on real-world deepfakes in published tests; its score is uncertain evidence, not a verdict.
- The scam-word lists are a draft and have not been reviewed by native speakers.
- Results so far come from a few clips of one speaker. Do not treat them as benchmarks.

## Licence
To be decided before the repository is made public.
