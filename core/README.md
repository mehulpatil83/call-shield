# core: analyse a recording

```
python -m core.analyse phase0\audio\en_scam.wav
python -m core.analyse phase0\audio\hinglish_scam.wav
python -m core.analyse some_call.m4a --lang mr
python -m core.analyse --text transcript.txt --lang en      (text only: no Gnani, no audio check)
python -m core.analyse call.wav --no-auth                    (skip the audio authenticity check)
```
Output goes to `reports\<name>.html` (open in a browser) and `reports\<name>.json`.
The file-name prefix (`en_`, `mr_`, `hi_`, `hinglish_`) selects the language, or pass `--lang`.

## How it works
1. **Gnani STT** (`gnani_client.py`): REST for clips up to 60 s, batch for longer ones. Hinglish is transcribed twice
   (`en-IN` Roman script and `hi-IN` Devanagari) and the findings are merged. Every call is cached in `.cache/`, so a
   repeat run is free; `.cache/gnani_ledger.csv` records estimated cost.
2. **Rule engine** (`rules.py`, word lists in `lexicon.py`): no model, every alert quotes the transcript.
   - request: asks for an OTP, PIN/password, money or remote access
   - pressure: urgency, threats, secrecy, "don't verify / don't hang up"
   - context: authority claims, KYC pretext
   - warning: "never share your OTP" wording; this is not counted as a request
   Levels: **high** = a request plus pressure or authority; **elevated** = a request alone or two pressure tactics;
   **low** = otherwise.
3. **Audio authenticity** (`authenticity.py`): pretrained AASIST-L on CPU, scores 4-second windows, takes the median,
   and says "inconclusive" when there is too little speech or the score is between the bands.
4. **Report** (`report.py`): two separate findings, evidence highlighted in the transcript, limitations box.

## Tests
```
python -m pytest tests -q
```
The tests use fake Gnani and a fake model, so they cost nothing and need no audio.
`tests/cases.py` holds scam, benign and hard-negative transcripts. NOTE: the word lists were written while looking at
these cases, so they are development tests, not an evaluation. The real evaluation (Phase 3) uses fresh recordings.

## Known limitations
- Draft word lists, not reviewed by native speakers.
- No speaker separation: cannot tell caller from callee.
- A legitimate call that asks for an OTP (for example a real delivery agent) is reported as "worth checking", by design.
- The authenticity bands are provisional and AASIST-L is weak on unseen real-world fakes.
