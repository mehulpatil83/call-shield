# app: local web interface

```
pip install -r requirements-app.txt
python -m app.run
```
Then open http://127.0.0.1:8000 (it opens by itself). The server only listens on this computer.

* Upload a recording, choose its language, tick the consent box, press Analyse.
* Progress is shown live; the report has the plain-language summary, "What to do now", evidence you can tap, the audio
  check with its score chart, the transcript and the limitations.
* History lists earlier analyses. Delete removes the audio, the report AND the cached transcript for that recording.
* Interface languages: English, Hindi, Marathi (the Hindi and Marathi text is a draft that needs native review).
* Where things are stored: `data/` (database, uploads, reports, per-recording cache). It is ignored by git.

## Live check (new)
Open the **Live check** tab. Tick the consent box, then either
* **Start listening**: uses the microphone (the browser asks permission; works on http://127.0.0.1:8000 and localhost), or
* **Replay a recording as a live call**: plays a file into the same pipeline at real-time speed. Best for demos and tests.

While audio streams to Gnani's streaming speech-to-text, the rules re-run on every new phrase: a risk meter moves, an alert
banner appears as soon as the call becomes "worth checking" or "high risk", and the transcript highlights the evidence.
Press **Stop** and the call is saved like any other analysis (audio, voice check, full report, history, delete).
* Streaming accepts one language code per stream, so Hinglish opens two streams (en-IN and hi-IN) and "Not sure" opens three.
  Cost is about Rs 0.47 per audio minute per stream. Calls stop automatically after 10 minutes.
* One live call at a time. The microphone audio is sent to Gnani only after the consent box is ticked.

## Two-person calls (speaker separation)
On the Upload tab choose a specific language and tick **This is a conversation between two people**. The report then judges
each speaker separately ("The warning signs come from Speaker 1"), including a voice check on each speaker's own audio.
* If the file is stereo with a different person on each channel, the channels are used (exact, and cheap).
* Otherwise Gnani's batch speech-to-text labels the speakers (diarization). It can mix up voices, and a single language
  code is used (Hinglish uses en-IN). Speaker separation is not available with "Not sure".
* Build a demo call from two of your own recordings: `python tools\make_stereo.py caller.wav victim.wav demo_call.wav`.
  Command line: `python -m core.analyse demo_call.wav --lang en --conversation`.

## Safety against other websites
The server refuses requests from other sites (a website you visit cannot make your browser spend credits or upload files
through it) and refuses unknown Host names. It only listens on 127.0.0.1.

## Rebuild the web page (only if you change `app/frontend/src`)
Needs Node.js 20+.
```
cd app\frontend
npm install
npm run build
npm test
```
For live editing run `python -m app.run --no-browser` in one window and `npm run dev` in another, then open the address
Vite prints.

## API (also at /api/docs)
`POST /api/analyses` (file, language, consent=true, skip_audio_check) · `GET /api/analyses` · `GET /api/analyses/{id}` ·
`GET /api/analyses/{id}/report.html` · `DELETE /api/analyses/{id}` · `DELETE /api/analyses` · `GET /api/health` ·
WebSocket `/api/live?language=&consent=true` (binary PCM16 mono 16 kHz in; JSON messages out)

## Privacy and safety choices
* No accounts and no cloud hosting; the only thing sent out is the audio itself, to Gnani, after the consent box is ticked.
* Uploads are limited to 25 MB and to wav/mp3/m4a/flac/ogg. IDs are random; file names are never used as paths.
* Transcripts are never written to logs. One analysis runs at a time (small CPU).
* The downloadable report is served with a strict content-security policy.
