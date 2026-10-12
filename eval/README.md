# eval: honest evaluation

Goal: measure how well call-shield really works, and say so plainly, including where it fails.

## The rules that keep the numbers honest
1. **Dev and test scripts.** `scripts_bank.py` splits the 24 reading scripts into DEV and TEST. Improve the word lists using
   DEV results only. Run TEST once, at the end. The tool records the word-list version used on the test scripts; if you
   change the lists after seeing test results, the report is marked as contaminated.
2. **More than one voice.** Ask people other than yourself to record. With fewer than 3 real speakers the report says so.
3. **Report failures.** `failures.csv` lists every wrongly rated recording. Put the interesting ones in the write-up.
4. **Say what was not tested:** real calls, two-person conversations, modern cloned voices, real phone networks.

## Workflow
```
python -m eval.text_baseline                       (rules only, perfect transcripts, dev scripts: instant and free)
python -m eval.run_eval --dry-run                  (cost estimate)
python -m eval.run_eval --split dev --conditions orig,tel8k
python -m eval.make_report eval\results\<run folder>
```
Then fix the word lists using the DEV failures, re-run, and repeat. When you are finished tuning:
```
python -m eval.text_baseline --split test --i-am-done-tuning
python -m eval.run_eval --split test --conditions orig,tel8k,tel8k_noisy
python -m eval.make_report eval\results\<run folder>
```
Other options: `--lang-mode auto` (tests the "not sure" option), `--no-auth` (skip the audio check), `--recordings <folder>`.

## Recordings
Put recordings in `eval\recordings\` (ignored by git: they are people's voices). Name: `<speaker>_<script id>.wav`,
e.g. `p1_en-s1.wav`. Add `_syn` for a synthetic voice reading the same script: `ai1_en-s1_syn.wav`.
Reading sheets for speakers are in `eval\scripts\` (en.md, hinglish.md, mr.md). See `recording_guide.md`.

## Conditions
`orig` the file as recorded; `tel8k` phone-line simulation (300-3400 Hz, 8 kHz, mu-law); `tel8k_noisy` the same with
noise at 15 dB. These are simulations, not real networks.

## What the tables mean
- *recall (high)*: scam recordings rated "high risk". *false alarms (high)*: benign recordings rated "high".
  The "any alert" columns also count "worth checking".
- Intervals are Wilson 95% and are wide with small samples. Read them, not just the percentage.
- *AUC*: chance that a random real voice scores above a random synthetic one (0.5 = coin flip).
- Hard cases are legitimate calls that sound suspicious (delivery code at the door, a real bank fraud alert).
