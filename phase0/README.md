# Phase 0 smoke tests (CPU edition)

The whole project runs on CPU. Phase 0 (Oct 11-12) answers: what do Gnani STT, the anti-spoofing model and a small
local LLM actually do on YOUR machine and YOUR voice, and how fast? About 30 minutes of Gnani audio (about Rs 15).

## What I verified, and what I could not
- Verified: every Gnani call matches the real `gnani-vachana` 0.8.1 SDK (signatures inspected from the installed
  package). Audio helpers, WER, variant generation, summary, the LLM quote-checker and the probes' control flow were
  tested offline against mocks.
- NOT verified: any live Gnani call, the model downloads, Windows, your CPU speed, the real model weights.
  Expect a few things to need a fix; that is what this phase is for. Paste any error back to me.

## Things I found in the SDK that change the plan
1. **Hinglish has no dedicated code.** The SDK rejects the `en-hi-in-cm` style codes I mentioned earlier. Batch STT
   accepts comma-separated codes such as `hi-IN,en-IN` (language identified per speaker turn) and `auto`.
   Streaming accepts only the 10 single codes.
2. **Batch STT has options to test and report:** server-side `denoise`, `bias_words` (+ `bias_score`) to push
   recognition toward OTP/KYC/UPI, `diarization` (up to 8 speakers), `multi_channel`.
3. **REST is limited to 60 s per file** and takes one code. `format="transcribe"` (number formatting) works for
   hi-IN and en-IN only; `verbatim` keeps spoken words, which suits our digit parser.
4. Streaming needs exact 1024-byte PCM frames at real-time pace, 8 kHz or 16 kHz.

## CPU-only design notes
- Gnani STT runs on Gnani's servers, so it costs your CPU nothing.
- Anti-spoofing: start with the tiny **AASIST-L**. **W2V2-AASIST** (about 318M parameters) is the better detector but
  heavy on CPU; the probe measures its real-time factor, and `--quantize` tests an int8 speed-up (and checks whether
  the scores change).
- The LLM must be small (3-4B, 4-bit) and is called only on flagged segments. The probe measures tokens/second.
- Run things one at a time on 16 GB RAM and close the browser during the heavy steps.

## No recordings yet? Use the placeholder clips
`audio/` already contains six SYNTHETIC clips (`en_synth_*.wav`, `hinglish_synth_*.wav`, `mr_synth_*.wav`) made with the
free espeak-ng voice from the same passages. They let you run every script today to check the plumbing: that Gnani
accepts the files, the language codes work, streaming connects, the credit ledger fills, and the anti-spoofing model
loads and runs. Limits to keep in mind:
- They sound robotic, so Gnani's WER on them says little about real speech. **Do not quote those numbers.**
- Anti-spoofing models should treat them as synthetic, which is a useful sanity check, not a real deepfake test.
- Hinglish was synthesised from the Devanagari version (`*.alt.txt`), which also tests the alternate-reference WER.
Later, record your own clips with the names in step 2 (`en_scam.wav`, ...) and rerun; real-voice numbers replace these.

Things you can do with NO audio at all: GitHub setup, environment setup, `python check_env.py`,
`python gnani_probe.py --list-languages`, the LLM test (step 8), and downloading the models
(`python antispoof_probe.py --model aasist-l --download` downloads first; it stops if there are no clips).

## Steps (Windows PowerShell)
**1. Setup**
```powershell
cd phase0
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env              # open .env and paste your Gnani API key
python check_env.py
```
**2. Record 6 clips.** Read each passage in `audio/*.txt` aloud, naturally, 20-40 s each, and save a WAV with the same
name: `audio/en_scam.wav`, `en_benign.wav`, `hinglish_scam.wav`, `hinglish_benign.wav`, `mr_scam.wav`, `mr_benign.wav`
(Windows Voice Recorder or Audacity; any sample rate). These are fictional scripts; do not use real names or numbers.

**3. Variants.** `python make_variants.py` (clean 16 kHz, phone-line 8 kHz, noisy phone-line, upsampled copy).

**4. Gnani REST.** Note your dashboard balance first.
```powershell
python gnani_probe.py --list-languages
python gnani_probe.py --dry-run
python gnani_probe.py
python gnani_probe.py --dir variants --only tel8k,tel8k_noisy
```
**5. Gnani batch options**
```powershell
python gnani_probe.py --mode batch --configs base,denoise,bias,diar
python gnani_probe.py --mode batch --configs mixed,auto
python gnani_probe.py --mode batch --dir variants --only tel8k --configs base,denoise,bias
```
**6. Streaming and credit metering**
```powershell
python gnani_stream_test.py en_scam.wav --rate 16000
python gnani_stream_test.py en_scam__tel8k.wav --rate 8000
python gnani_stream_test.py mr_scam.wav --rate 16000 --idle 60
```
Check the balance after the idle run. If it dropped more than the audio length explains, idle time is billed.

**7. Anti-spoofing (CPU)**
```powershell
python antispoof_probe.py --model aasist-l --download
python antispoof_probe.py --model aasist-l --quantize        # optional
python antispoof_probe.py --model w2v2 --download            # needs fairseq; may fail on Windows - send me the error
```
Optional easy fake voice: `pip install pyttsx3`, `python make_synthetic.py`, `python make_variants.py`, rerun.
No universal threshold exists yet; we are checking that it runs, seconds per window, RAM, and how scores move
between clean and phone-quality audio.

**8. Local LLM (CPU)**: install Ollama from https://ollama.com/download, then
```powershell
ollama pull qwen2.5:3b
ollama pull llama3.2:3b
python llm_probe.py --models qwen2.5:3b,llama3.2:3b
```
It reads `audio/*.txt` (no audio, no credits). Check that scam passages get tactics, benign ones get
`legitimate_warning`, quotes are verified, and see tokens/second. Marathi is the likely weak spot.

**9. Optional Whisper second opinion (CPU):** `pip install faster-whisper`, then `python whisper_probe.py --model small`.

**10. Summary:** `python summarize.py`

## Send me back
1. Console output of steps 1, 4-9 and the contents of `results/`.
2. Dashboard balance before/after steps 4-5 and 6 (including the idle test).
3. Anything surprising: errors, odd transcripts, wrong script (Devanagari vs Roman), slow responses.

## Reading the results
- For Hinglish, WER against the Roman-script text can look terrible even when the transcript is right, because the
  service may answer in Devanagari. Read the transcript and the `terms found` line, or add
  `audio/hinglish_scam.alt.txt` with the same text in Devanagari (WER then uses the closer reference).
- Our phone-line simulation (band-pass, 8 kHz, mu-law) is an approximation, not a real network codec.
- Six clips is a smoke test, not a benchmark. It tells us what is broken, not how good anything is.
