# Call mode, Part 1: phone Speaker -> laptop Receiver

You talk on the phone (Speaker). The laptop (Receiver) shows the live check: risk meter, alert, highlighted evidence,
transcript and "what to do now". The phone shows a plain call screen and never any analysis.

## Call console (laptop, while the call runs)
When the phone connects, the Receiver page switches to a two-column console designed for a laptop screen (best at 1366x768 or larger).
* **Right half: a phone call simulation.** The protected person's phone: caller card ("Unknown caller"), call timer, live captions with the risky words highlighted, a risk strip (low, elevated, high), Speaker and Hang up buttons. At elevated risk an amber strip appears on the phone; at high risk the red warning, advice and evidence take over the phone screen.
* **Left half:**
  * Live status, timer, risk meter, audio level and the Listen and End controls.
  * **Risk over time:** a graph of the rule-based score (0 to 10), coloured by level, with markers where each alert fired. **Hover or focus a point** to see what was heard at that moment.
  * **What the caller wants**, the **tactic board** (tiles light up as each tactic is heard), and **what to do now**.
  * **Timeline:** every tactic and alert with the time it was first seen. **Select an item** and those exact words light up in the phone's captions, with a short "why this matters".
  * **Call details:** duration, estimated cost in rupees (0.47 per minute per speech stream, an estimate), detection engine, voice-check note, and the alert settings.
  * **Demo scripts drawer** with four acted English scripts and a Copy button. It is also on the page before the call.
* **After the call: a scorecard** with the verdict, time to the first warning, time to the high alert, time of the first request for something sensitive, the tactics heard, the highest score, and the Open report button.
* Times and the graph use the audio time reported with each analysis update, so they can lag the speech by a few seconds. The score comes from the rules, so the line moves in steps.

## What each screen shows
* **Phone (Speaker):** call timer, a microphone level bar, a warning if nothing has been heard for 8 seconds (not shown while muted), mute and end buttons. If the connection drops or the screen locks it says so and keeps trying to rejoin the same call for 60 seconds. After a page reload it offers a "Rejoin the call" button.
* **Laptop (Receiver):** risk meter, alert, highlighted evidence, transcript, "what to do now", a "Receiving audio" indicator with a level bar (it warns if no audio arrives for 3 seconds, or only silence for 5), and a banner while the phone is reconnecting.

## Alert experience (laptop)
* **Elevated risk:** an amber banner and one soft beep.
* **High risk:** a full-screen red warning with the top three pieces of advice, the strongest evidence quotes (requests first; cautionary wording is never shown as evidence), a short siren, and the advice spoken aloud in the interface language (English, Hindi or Marathi). The browser tab title also flashes "SCAM WARNING" so it is noticeable from another tab.
* It fires once per step up (elevated, then high) per call, and again for the next call. Dismiss it with the button or Escape. It closes by itself when the call ends so it never covers the report.
* **Alert settings** (a panel above the meter, remembered in the browser): Beep, Speak the advice aloud, Full-screen warning.
* Nothing is downloaded: the siren is generated and the speech uses the browser's own voices. If the device has no voice for Hindi or Marathi, the advice stays on screen and the page says so; Marathi falls back to a Hindi voice if one is installed.
* **Same-room warning:** if the phone is next to the laptop, its microphone can pick up the spoken alert and send it back into the analysis. Use headphones, keep the phone in another room, or switch Speak off. The slow pulse animation is skipped for people who set "reduce motion".

## How it works
```
phone browser --(wss, PCM16 16 kHz)--> Cloudflare tunnel --> 127.0.0.1:8000 (this laptop)
                                                              |-> LiveSession -> Gnani streaming STT -> rules
laptop browser (http://127.0.0.1:8000/#/call) <-- analysis messages <-+
```
The server stays bound to 127.0.0.1. The tunnel program connects to it locally and gives the phone a valid https address,
which is what a phone needs before it will allow the microphone.

## Run the demo (about 3 minutes)
1. One time: `winget install --id Cloudflare.cloudflared`, then open a new Command Prompt.
2. In the Command Prompt where your Python environment is active: `tools\start_demo.bat`
3. The Receiver page opens. If the public address box is empty, paste the `https://....trycloudflare.com` address from the tunnel window.
4. Tick the consent box, choose English, press **Start the call**. A QR code and a 6-digit code appear.
5. On the phone (Android Chrome): scan the QR code (or open the address and type the code), tick consent, press **Join the call**, allow the microphone.
6. Speak an acted script. The laptop shows the meter, alert, evidence and advice within a few seconds.
7. Press **End call** on the phone (or **End the call and get the report** on the laptop), then open the report. Delete it when done.

Use headphones on the laptop, or leave **Listen** off (default). Keep the phone screen on during the call.

## Acted, fictional scripts (English)
* Scam: "Hello sir, I am calling from your bank's security department. Your account will be blocked today unless you verify right now. Please share the six digit OTP that you just received."
* Friendly: "Hi, are we still meeting for lunch at one? I will bring the notes from class. Let me know if the cafe is too crowded and we can go somewhere else."
* Bank warning (must not be flagged): "This is a reminder from your bank. Never share your OTP, PIN or password with anyone, even if they say they are calling from the bank."

Text-only rule check of these three: scam = high (7.0), friendly = low (0.0), bank warning = low (1.0).
Not yet measured: how Gnani's speech-to-text transcribes them when spoken into a phone over the tunnel.

## Security model
* On the tunnel address only these are allowed: GET/HEAD of the web page's static files, and the Speaker WebSocket. Everything under `/api` (history, reports, uploads, the Receiver socket, the plain live check, docs) answers 403 there.
* Any other Host header is refused with 400 (as before).
* A call code is 6 digits, works once, expires after 10 minutes, and wrong guesses are limited to 8 per minute per client. Only one Speaker and one Receiver can join.
* The server accepts no audio before the Speaker's consent message. Starting a call needs the Receiver's consent too.
* Only act-out speech. No real phone numbers, account numbers, Aadhaar, PAN or recorded calls.

## Detection: what changed in this version
* New phrase patterns for the fake fraud-department opening (suspicious activity, unauthorised charges, verify your identity, card ending, secure authorization token, "we are holding this transaction", safe account, refund and prize pretexts).
* A problem with your account reported together with a claim of authority, or together with an identity check, is now rated **elevated** even before anything is requested. A request for a code or money on top of that is still **high**.
* Speech-to-text tolerance: inflections (verify / verifying), words split or joined differently ("pass word", "any desk"), and a short list of known slips read as the word probably meant ("diverse" as "reverse" next to "charges", "flat" as "flagged"). The evidence always quotes what was actually heard. Add your own slips in `core/lexicon.py` (`STT_SLIPS`). Dropped words, such as the department name on your first call, cannot be recovered.
* Still rule-based only: no model reads the transcript. The only model is the voice-authenticity one.

## Evaluation (rules, perfect transcripts)
`python -m eval.call_eval --split all --i-am-done-tuning`. Twenty acted English scripts; I tuned on the dev half and on your real call only.

| | Before | After |
|---|---|---|
| Dev scams rated high | 3 of 5 (1 missed, 1 only elevated) | 5 of 5 |
| Test scams rated high | 3 of 5 (2 only elevated) | 3 of 5 (2 only elevated) |
| Benign calls with a false alarm | 0 of 10 | 0 of 10 (including 4 hard cases) |
| Your real call: first alert | 41.6 s (high) | 33.6 s (elevated), 41.6 s (high) |

* Times assume 150 words per minute and exclude speech-to-text delay.
* The test half did not improve because I did not tune on it. It shows two real gaps: "transfer the amount to the account number I give you" and "send two thousand rupees to this number" are not recognised as payment requests. Next time: move those two scripts to dev, fix them, and write fresh test scripts.
* I saw the test results once, before tuning, to record the baseline. The same author wrote scripts and word lists, so these numbers are optimistic. Your own recordings are the real test.

## Known limits (be honest about these)
* Tested here: 154 Python tests, 60 web tests, and runs over a real local server with real WebSockets, including a connection that vanishes and rejoins (fake speech-to-text stream).
  **Not tested here:** a real phone, the real tunnel, Android Chrome's microphone and screen-lock behaviour, real Gnani streaming through this path, and the real rejoin after a locked screen.
* Rejoin: the server keeps the call and the speech-to-text streams open for 60 seconds, sending silence to keep them alive (not stored in the report). Gnani bills streamed time, so each drop can cost up to about 60 seconds of one stream (roughly ₹0.50). If Chrome kills the page, tap **Rejoin the call**. If the phone is gone for more than 60 seconds, the call ends and the report keeps what was heard.
* Only the same phone can rejoin: it holds a secret token that the Receiver never sees. A new phone cannot join a call that has started.
* The cloudflared address auto-detect (via its local metrics port 20241) is best effort. If it fails, paste the address by hand.
* Same-room use: the phone microphone can pick up the laptop's sound if Listen is on. Use headphones or two rooms.
* A legitimate delivery person asking for the delivery code, or a genuine bank alert, can still be rated elevated. That is by design: the advice (call the official number) is right either way.
* Hindi and Marathi strings for call mode are AI drafts and need a native-speaker review.
* The free quick tunnel gives a new address every time you start it and has no uptime guarantee.
* One live analysis at a time; 10-minute cap; Hinglish uses 2 Gnani streams (about Rs 0.47 per minute each).

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Phone says the microphone is blocked | Allow it in Chrome's site settings for the tunnel address, then rejoin |
| "That code is not valid" | Code expired (10 min), already used, or typed wrongly. Start a new call |
| "The receiver is not ready yet" | The Receiver page was closed. Start the call again |
| Phone page does not load | Tunnel window closed, or the address changed. Restart `tools\start_demo.bat` |
| Meter stays at low with no transcript | Speaking too quietly, wrong language chosen, or the Gnani key is missing in `.env` |
| Echo or feedback | Turn Listen off, use headphones |
| Phone shows "We cannot hear you" | Not muted? Move closer, check Chrome's microphone permission, and that no other app is using the microphone |
| Laptop says "No audio is arriving" | The phone page is closed, locked or offline. Wait for the reconnect banner or ask the phone to tap Rejoin |

## Next parts
* Part 2: two-way conversation, analysis while both sides speak. The server already receives the Speaker's audio and now keeps a call alive across drops; Part 2 adds the Receiver's own microphone and per-speaker analysis.
* Part 3: to be defined.
