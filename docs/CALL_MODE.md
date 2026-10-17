# Call mode, Part 1: phone Speaker -> laptop Receiver

You talk on the phone (Speaker). The laptop (Receiver) shows the live check: risk meter, alert, highlighted evidence,
transcript and "what to do now". The phone shows a plain call screen and never any analysis.

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

## Known limits (be honest about these)
* Tested here: 121 Python tests, 45 web tests, and a run over a real local server with real WebSockets using a fake speech-to-text stream.
  **Not tested here:** a real phone, the real tunnel, Android Chrome's microphone, real Gnani streaming through this path.
* The cloudflared address auto-detect (via its local metrics port 20241) is best effort. If it fails, paste the address by hand.
* If the phone loses connection or its screen locks, the call ends (the report is still stored). Rejoining the same call is not supported yet.
* Same-room use: the phone microphone can pick up the laptop's sound if Listen is on. Use headphones or two rooms.
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

## Next parts
* Part 2: two-way conversation, analysis while both sides speak. The server already receives the Speaker's audio; Part 2 adds the Receiver's own microphone and per-speaker analysis.
* Part 3: to be defined.
