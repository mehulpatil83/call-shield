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
`GET /api/analyses/{id}/report.html` · `DELETE /api/analyses/{id}` · `DELETE /api/analyses` · `GET /api/health`

## Privacy and safety choices
* No accounts and no cloud hosting; the only thing sent out is the audio itself, to Gnani, after the consent box is ticked.
* Uploads are limited to 25 MB and to wav/mp3/m4a/flac/ogg. IDs are random; file names are never used as paths.
* Transcripts are never written to logs. One analysis runs at a time (small CPU).
* The downloadable report is served with a strict content-security policy.
