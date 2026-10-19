import type { Lang, Level, SpeechLang, Step } from './types'

export interface CategoryText { label: string; explain: string }
export interface LiveText {
  title: string
  intro: string
  micHint: string
  startMic: string
  replay: string
  stop: string
  connecting: string
  listening: string
  stopping: string
  meter: string
  alertHigh: string
  alertElevated: string
  openReport: string
  again: string
  limitReached: (seconds: number) => string
  tooShort: string
  waiting: string
  spotted: string
  warningNote: string
}
export interface AlertText {
  headline: string
  subline: string
  elevated: string
  dismiss: string
  repeat: string
  settings: string
  sound: string
  voice: string
  fullscreen: string
  echoNote: string
  noVoice: string
  heard: string
  spoken: string
  titleFlash: string
}
export interface CallText {
  nav: string
  title: string
  intro: string
  publicLabel: string
  publicHint: string
  noTunnel: string
  consent: string
  start: string
  cancel: string
  end: string
  codeLabel: string
  scan: string
  joinAddress: string
  waitingSpeaker: string
  speakerJoined: string
  listen: string
  listenHint: string
  expires: (minutes: number) => string
  speakerTitle: string
  speakerIntro: string
  codeInput: string
  codeInvalid: string
  speakerConsent: string
  join: string
  connecting: string
  connected: string
  muted: string
  mute: string
  unmute: string
  endCall: string
  ended: string
  joinAnother: string
  micDenied: string
  keepScreenOn: string
  lostConnection: string
  roleSpeaker: string
  nothingShown: string
  levelLabel: string
  speakHint: string
  silenceWarning: string
  reconnecting: string
  rejoinTitle: string
  rejoinButton: string
  receiverReconnecting: (seconds: number) => string
  receivingAudio: string
  audioLevelLabel: string
  audioNone: string
  audioSilent: string
}
export interface SpeakerText {
  title: string
  word: string
  checkbox: string
  hint: string
  who: (label: string) => string
  nobody: string
  noSigns: string
  voice: string
  noteDiarization: string
  noteChannels: string
  noteSingle: string
}
export interface Dict {
  code: 'en' | 'hi' | 'mr'
  alert: AlertText
  speakers: SpeakerText
  nav: { upload: string; live: string; call: string }
  live: LiveText
  call: CallText
  appName: string
  tagline: string
  privacy: string
  interfaceLanguage: string
  uploadTitle: string
  chooseFile: string
  dropHint: string
  noFile: string
  languageLabel: string
  langs: Record<SpeechLang, string>
  consent: string
  skipAudio: string
  analyse: string
  keyMissing: string
  tooBig: (mb: number) => string
  working: string
  steps: Record<'queued' | Step, string>
  failedTitle: string
  back: string
  newAnalysis: string
  history: string
  noHistory: string
  open: string
  delete: string
  deleteAll: string
  confirmDelete: string
  confirmDeleteAll: string
  download: string
  levels: Record<Level, string>
  plain: Record<Level, string>
  advice: Record<Level, string[]>
  whatToDo: string
  conversation: string
  authenticity: string
  evidence: string
  minor: string
  minorNote: string
  unreliable: string
  unreliablePlain: string
  unreliableAdvice: string[]
  languageWarning: Record<'not_english' | 'not_devanagari', string>
  noEvidence: string
  transcript: string
  transcriptHint: string
  legend: Record<'request' | 'pressure' | 'context' | 'warning', string>
  spokenNumbers: string
  digitNote: string
  digitsCount: (n: number) => string
  limitations: string
  limits: string[]
  auth: Record<'natural' | 'synthetic' | 'inconclusive_band' | 'inconclusive_short' | 'unavailable', string>
  authNote: string
  medianLine: (median: number, q25: number, q75: number, windows: number) => string
  chartTitle: string
  bandNatural: string
  bandSynthetic: string
  provisional: string
  categories: Record<string, CategoryText>
}

const en: Dict = {
  speakers: {
    title: 'Who said what',
    word: 'Speaker',
    checkbox: 'This is a conversation between two people (separate the speakers)',
    hint: 'Needs a specific language (not "Not sure") and takes longer. Works best when each person is on a separate stereo channel.',
    who: (label) => `The warning signs come from ${label}.`,
    nobody: 'No speaker stood out as suspicious.',
    noSigns: 'No scam signs from this speaker.',
    voice: 'Voice check',
    noteDiarization: "Speakers were separated by Gnani's speaker labelling (diarization). It can mix up voices.",
    noteChannels: 'Speakers were separated using the two stereo channels.',
    noteSingle: 'Only one speaker was detected, so this is the same as a normal analysis.',
  },
  alert: {
    headline: 'यह कॉल ठगी जैसी लगती है',
    subline: 'कोई कोड, पिन, पासवर्ड या भुगतान की जानकारी न बताएँ।',
    elevated: 'सावधान: इस कॉल में खतरे के संकेत हैं। जाँच किए बिना कोई कोड या पैसा न दें।',
    dismiss: 'समझ गया',
    repeat: 'फिर से सुनाएँ',
    settings: 'अलर्ट सेटिंग',
    sound: 'बीप',
    voice: 'सलाह बोलकर सुनाएँ',
    fullscreen: 'पूरी स्क्रीन की चेतावनी',
    echoNote: 'अगर फ़ोन उसी कमरे में है तो वह बोला गया अलर्ट पकड़ सकता है। हेडफ़ोन लगाएँ, या फ़ोन को दूसरे कमरे में रखें।',
    noVoice: 'इस डिवाइस पर इस भाषा की आवाज़ इंस्टॉल नहीं है, इसलिए सलाह केवल स्क्रीन पर दिखेगी।',
    heard: 'क्या सुना गया',
    spoken: 'सावधान। यह कॉल ठगी जैसी लगती है। कोई कोड या भुगतान की जानकारी न बताएँ। फ़ोन काट दें और अपने कार्ड के पीछे छपे नंबर पर बैंक को कॉल करें।',
    titleFlash: 'ठगी की चेतावनी',
  },
  nav: { upload: 'Upload a recording', live: 'Live check', call: 'Receive a call' },
  call: {
    nav: 'Receive a call',
    title: 'Receive a call',
    intro: 'Start a call, then scan the code or open the address on the phone that will be the Speaker. This computer is the Receiver: it listens to the call and shows the live check. Use only acted, fictional speech, never real personal, bank or ID details.',
    publicLabel: 'Public address (from the tunnel window)',
    publicHint: 'Start the tunnel first (tools\\start_demo.bat). The address looks like https://something.trycloudflare.com',
    noTunnel: 'No tunnel address yet, so a phone cannot join. You can still test with a second browser tab on this computer.',
    consent: 'I understand that the Speaker\'s voice is sent from their phone to this computer and then to Gnani for transcription, and that everyone on the call has agreed. Only acted, fictional speech is used.',
    start: 'Start the call',
    cancel: 'Cancel the call',
    end: 'End the call and get the report',
    codeLabel: 'Call code',
    scan: 'On the phone: scan this code, or open the address below and type the code.',
    joinAddress: 'Join address',
    waitingSpeaker: 'Waiting for the Speaker to join…',
    speakerJoined: 'The Speaker has joined and is confirming consent…',
    listen: 'Listen to the call on this device',
    listenHint: 'Off by default. Use headphones, or keep the phone in another room, otherwise the phone picks up this computer\'s sound and you get an echo.',
    expires: (m) => `The code works once and for ${m} minutes.`,
    speakerTitle: 'Join a call as Speaker',
    speakerIntro: 'You are the Speaker. Your voice goes to the Receiver\'s computer, which checks the call for scam tactics. Nothing of that check is shown on this phone.',
    codeInput: 'Call code (6 digits)',
    codeInvalid: 'Enter the 6-digit code shown on the Receiver\'s screen.',
    speakerConsent: 'I agree that my voice is sent to the Receiver\'s computer and to Gnani for speech-to-text and analysis. I will say only acted, fictional lines, never real personal, bank or ID details.',
    join: 'Join the call',
    connecting: 'Connecting…',
    connected: 'Connected. You can speak now.',
    muted: 'Muted',
    mute: 'Mute',
    unmute: 'Unmute',
    endCall: 'End call',
    ended: 'The call has ended.',
    joinAnother: 'Join another call',
    micDenied: 'The microphone is blocked. Allow it in the browser\'s site settings and try again.',
    keepScreenOn: 'Keep this screen on during the call, or the phone stops sending your voice.',
    lostConnection: 'The connection was lost.',
    roleSpeaker: 'Speaker',
    nothingShown: 'This phone shows no analysis.',
    levelLabel: 'Microphone level',
    speakHint: 'Speak and watch the bar move.',
    silenceWarning: 'We cannot hear you. Check that you are not muted, move closer to the microphone, and that the microphone is allowed.',
    reconnecting: 'Connection lost. Trying to rejoin the call…',
    rejoinTitle: 'Your call may still be running',
    rejoinButton: 'Rejoin the call',
    receiverReconnecting: (s) => `The phone lost its connection. Waiting up to ${s} seconds for it to rejoin…`,
    receivingAudio: 'Receiving audio from the phone',
    audioLevelLabel: 'Incoming audio level',
    audioNone: 'No audio is arriving from the phone.',
    audioSilent: 'The phone is sending silence: it may be muted, or nobody is speaking.',
  },
  live: {
    title: 'Live check',
    intro: 'Listen to a call as it happens, or replay a recording as if it were live. The risk meter updates as words are recognised. Use this only with the permission of everyone on the call.',
    micHint: 'Your browser will ask for permission to use the microphone. Open this page at http://127.0.0.1:8000 or localhost.',
    startMic: 'Start listening (microphone)',
    replay: 'Replay a recording as a live call',
    stop: 'Stop and get the report',
    connecting: 'Connecting…',
    listening: 'Listening…',
    stopping: 'Finishing and saving the report…',
    meter: 'Risk so far',
    alertHigh: 'Warning: this call shows signs of a scam. Do not share any code, PIN or password. Hang up and call your bank on its official number.',
    alertElevated: 'Be careful: something sensitive is being asked for. Check who is really asking before you share anything.',
    openReport: 'Open the full report',
    again: 'Start another',
    limitReached: (n) => `The ${n}-second limit was reached, so the check was stopped.`,
    tooShort: 'The call was too short to analyse.',
    waiting: 'Waiting for speech…',
    spotted: 'Spotted so far',
    warningNote: 'A speech-recognition stream reported a problem; the check continues.',
  },
  code: 'en',
  appName: 'call-shield',
  tagline: 'Check a call recording for scam tactics and for signs of a synthetic voice.',
  privacy: 'Analysis runs on this computer. Recordings are kept only in the local data folder and you can delete them here at any time.',
  interfaceLanguage: 'Interface language',
  uploadTitle: 'Analyse a recording',
  chooseFile: 'Choose an audio file',
  dropHint: 'or drop it here (WAV, MP3, M4A, FLAC or OGG)',
  noFile: 'No file chosen',
  languageLabel: 'Language spoken in the recording',
  langs: { auto: 'Not sure (checks English, Hindi and Marathi; about 3x the cost)', en: 'English', hinglish: 'Hinglish (Hindi and English mixed)', mr: 'Marathi', hi: 'Hindi' },
  consent: "I have permission from everyone in this recording to analyse it. I understand the audio is sent to Gnani's speech service to be transcribed.",
  skipAudio: 'Skip the voice check (faster)',
  analyse: 'Analyse',
  keyMissing: 'The Gnani API key was not found, so transcription will fail. Add it to the .env file and restart the server.',
  tooBig: (mb) => `This file is larger than ${mb} MB.`,
  working: 'Working…',
  steps: { queued: 'Waiting', transcribing: 'Transcribing with Gnani', analysing: 'Looking for scam tactics', checking_audio: 'Checking the voice' },
  failedTitle: 'The analysis failed',
  back: 'Back',
  newAnalysis: 'Analyse another recording',
  history: 'Earlier analyses',
  noHistory: 'Nothing here yet.',
  open: 'Open',
  delete: 'Delete',
  deleteAll: 'Delete everything',
  confirmDelete: 'Delete this recording and its report?',
  confirmDeleteAll: 'Delete all recordings and reports?',
  download: 'Download report (HTML)',
  levels: { high: 'High risk', elevated: 'Worth checking', low: 'No scam tactics found' },
  plain: {
    high: 'This call shows several signs of a scam.',
    elevated: 'Something sensitive is being asked for. Check who is really asking before you share anything.',
    low: 'No scam tactics were found in this recording.',
  },
  advice: {
    high: [
      'Do not share any code, PIN, password or payment details.',
      'Hang up. Call your bank on the number printed on the back of your card or on its official website.',
      'Do not install any app or click any link this caller sent.',
      'If you already shared something, call your bank straight away to block the account or card. In India you can also report cyber fraud on helpline 1930 or at cybercrime.gov.in.',
    ],
    elevated: [
      'Only share a code with someone you contacted yourself and trust.',
      'If you are not sure, hang up and call the official number instead.',
    ],
    low: ['This is a decision aid, not a guarantee. If anything still feels wrong, hang up and call the official number.'],
  },
  whatToDo: 'What to do now',
  conversation: 'What is said',
  authenticity: 'How the voice sounds',
  evidence: 'Evidence',
  minor: 'Minor signals',
  minorNote: 'These alone are not enough to raise the risk level.',
  unreliable: 'Could not be checked reliably',
  unreliablePlain: 'The transcript does not look like the language you chose, so "no scam tactics found" cannot be trusted.',
  unreliableAdvice: [
    'Delete this analysis and upload the recording again with the correct language, or choose "Not sure".',
    'If the call felt suspicious, treat it as suspicious: do not share any code and call the bank on its official number.',
  ],
  languageWarning: {
    not_english: 'This transcript does not look like English. If the recording is in another language, the scam check can miss things.',
    not_devanagari: 'This transcript is not in the Devanagari script expected for the language you chose. The scam check can miss things.',
  },
  noEvidence: 'No indicators matched.',
  transcript: 'Transcript',
  transcriptHint: 'Tap a highlighted phrase to see why it was flagged.',
  legend: { request: 'request', pressure: 'pressure', context: 'claim or pretext', warning: 'warning wording' },
  spokenNumbers: 'Spoken number sequences',
  digitNote: 'Spoken number sequences are shown for context only and do not change the risk level. Reading a code aloud to a stranger is a warning sign.',
  digitsCount: (n) => `${n} digits`,
  limitations: 'Limitations',
  limits: [
    'The scam-word lists are a draft and have not been reviewed by native speakers.',
    'The transcript comes from speech-to-text; mistakes there can hide or invent scam words.',
    'Speakers are not separated, so the report cannot tell who said what.',
    'The voice check uses a small pretrained model that is weak on fakes it has not seen (about 44% error on a published real-world test set). Its score is uncertain evidence, never proof.',
    "The voice check can miss modern AI-generated voices, so 'no sign found' does not mean the voice is human.",
    'A real person can run a scam, and a synthetic voice can say something harmless. The two checks are independent.',
    "Audio was sent to Gnani's service for transcription. Only analyse recordings with the speakers' consent.",
  ],
  auth: {
    natural: 'No sign of synthetic speech found (weak check)',
    synthetic: 'Synthetic-sounding (provisional)',
    inconclusive_band: 'Inconclusive: the score is between the two bands',
    inconclusive_short: 'Inconclusive: too little speech',
    unavailable: 'Not available',
  },
  authNote: 'This check only looks at how the voice sounds. It cannot show who a caller really is. Modern AI-generated (text-to-speech) and cloned voices can easily pass it.',
  medianLine: (m, a, b, n) => `Median score ${m} (middle half ${a} to ${b}) over ${n} window(s) of about 4 seconds.`,
  chartTitle: 'Score for each 4-second window',
  bandNatural: 'natural',
  bandSynthetic: 'synthetic',
  provisional: 'The bands are provisional and will be recalibrated in the evaluation phase.',
  categories: {
    otp_request: { label: 'Asks for a one-time code (OTP)', explain: 'Banks and genuine services never need you to read a one-time code out to them.' },
    credential_request: { label: 'Asks for a PIN, password or card/ID number', explain: 'Nobody legitimate needs your PIN or password on a call.' },
    payment_request: { label: 'Asks for money or a payment', explain: 'Asks for money, a transfer or a payment link.' },
    remote_access: { label: 'Asks you to install a remote-control app', explain: 'Remote-control apps let a stranger operate your phone or computer.' },
    urgency: { label: 'Rushes you', explain: 'Pushes you to act immediately so you do not stop and think.' },
    threat: { label: 'Threatens a consequence', explain: 'Threatens a blocked account, legal action or disconnection to scare you into complying.' },
    secrecy: { label: 'Asks you to keep it secret', explain: 'Stops you from checking with anyone.' },
    verification_bypass: { label: 'Discourages checking', explain: 'Discourages you from verifying, hanging up or following the normal process.' },
    authority: { label: 'Claims to be a bank or authority', explain: 'Scammers claim authority to gain trust.' },
    kyc_pretext: { label: 'Uses a KYC pretext', explain: 'KYC updates are a very common opening in bank scams.' },
    account_alert: { label: 'Claims a problem with your account', explain: 'Fake fraud-department calls often open with suspicious activity or unauthorised charges, or offer a refund or prize.' },
    warning_otp: { label: 'Warning about sharing codes', explain: 'Cautionary wording such as "never share your OTP". Treated as a warning, not a request.' },
    warning_cred: { label: 'Warning about sharing a PIN or password', explain: 'Cautionary wording. Treated as a warning, not a request.' },
  },
}

// DRAFT translations written by an AI assistant: they need review by native Hindi and Marathi speakers.
const hi: Dict = {
  speakers: {
    title: 'किसने क्या कहा',
    word: 'वक्ता',
    checkbox: 'यह दो लोगों की बातचीत है (वक्ताओं को अलग करें)',
    hint: 'इसके लिए कोई खास भाषा चुननी होगी ("पक्का नहीं" नहीं) और इसमें ज़्यादा समय लगता है। जब हर व्यक्ति अलग स्टीरियो चैनल पर हो तो सबसे अच्छा चलता है।',
    who: (label) => `ठगी के संकेत ${label} की ओर से आ रहे हैं।`,
    nobody: 'कोई वक्ता संदिग्ध नहीं दिखा।',
    noSigns: 'इस वक्ता की ओर से ठगी के कोई संकेत नहीं।',
    voice: 'आवाज़ की जाँच',
    noteDiarization: 'वक्ताओं को Gnani की वक्ता-पहचान (डायराइज़ेशन) से अलग किया गया। यह आवाज़ों को आपस में मिला सकती है।',
    noteChannels: 'वक्ताओं को दो स्टीरियो चैनलों से अलग किया गया।',
    noteSingle: 'सिर्फ़ एक वक्ता मिला, इसलिए यह सामान्य जाँच जैसा ही है।',
  },
  alert: {
    headline: 'हा कॉल फसवणुकीसारखा वाटतो',
    subline: 'कोणताही कोड, पिन, पासवर्ड किंवा पेमेंटची माहिती सांगू नका.',
    elevated: 'सावध रहा: या कॉलमध्ये धोक्याची चिन्हे आहेत. तपासल्याशिवाय कोणताही कोड किंवा पैसे देऊ नका.',
    dismiss: 'समजले',
    repeat: 'पुन्हा सांगा',
    settings: 'अलर्ट सेटिंग',
    sound: 'बीप',
    voice: 'सल्ला मोठ्याने सांगा',
    fullscreen: 'पूर्ण स्क्रीन इशारा',
    echoNote: 'फोन त्याच खोलीत असेल तर तो बोललेला अलर्ट पकडू शकतो. हेडफोन वापरा, किंवा फोन दुसऱ्या खोलीत ठेवा.',
    noVoice: 'या डिव्हाइसवर या भाषेचा आवाज इन्स्टॉल केलेला नाही, म्हणून सल्ला फक्त स्क्रीनवर दिसेल.',
    heard: 'काय ऐकले गेले',
    spoken: 'सावधान. हा कॉल फसवणुकीसारखा वाटतो. कोणताही कोड किंवा पेमेंट तपशील सांगू नका. फोन कट करा आणि कार्डच्या मागे छापलेल्या नंबरवर बँकेला कॉल करा.',
    titleFlash: 'फसवणुकीचा इशारा',
  },
  nav: { upload: 'रिकॉर्डिंग अपलोड करें', live: 'लाइव जाँच', call: 'कॉल रिसीव करें' },
  call: {
    nav: 'कॉल रिसीव करें',
    title: 'कॉल रिसीव करें',
    intro: 'कॉल शुरू करें, फिर जिस फ़ोन को स्पीकर बनना है उस पर कोड स्कैन करें या पता खोलें। यह कंप्यूटर रिसीवर है: यह कॉल सुनता है और लाइव जाँच दिखाता है। केवल अभिनय की हुई, काल्पनिक बातें बोलें, असली निजी, बैंक या पहचान की जानकारी कभी नहीं।',
    publicLabel: 'सार्वजनिक पता (टनल वाली विंडो से)',
    publicHint: 'पहले टनल शुरू करें (tools\\start_demo.bat)। पता कुछ ऐसा दिखता है: https://something.trycloudflare.com',
    noTunnel: 'अभी टनल का पता नहीं है, इसलिए फ़ोन जुड़ नहीं सकता। आप इसी कंप्यूटर पर दूसरे ब्राउज़र टैब से जाँच कर सकते हैं।',
    consent: 'मैं समझता/समझती हूँ कि स्पीकर की आवाज़ उसके फ़ोन से इस कंप्यूटर और फिर ट्रांसक्रिप्शन के लिए Gnani को भेजी जाती है, और कॉल में सभी की सहमति है। केवल अभिनय की हुई, काल्पनिक बातें इस्तेमाल होंगी।',
    start: 'कॉल शुरू करें',
    cancel: 'कॉल रद्द करें',
    end: 'कॉल खत्म करें और रिपोर्ट पाएँ',
    codeLabel: 'कॉल कोड',
    scan: 'फ़ोन पर: यह कोड स्कैन करें, या नीचे का पता खोलकर कोड लिखें।',
    joinAddress: 'जुड़ने का पता',
    waitingSpeaker: 'स्पीकर के जुड़ने का इंतज़ार…',
    speakerJoined: 'स्पीकर जुड़ गया है और सहमति की पुष्टि कर रहा है…',
    listen: 'इस डिवाइस पर कॉल सुनें',
    listenHint: 'शुरू में बंद रहता है। हेडफ़ोन लगाएँ, या फ़ोन को दूसरे कमरे में रखें, वरना फ़ोन इस कंप्यूटर की आवाज़ पकड़कर गूँज बनाएगा।',
    expires: (m) => `कोड एक बार और ${m} मिनट तक चलता है।`,
    speakerTitle: 'स्पीकर के रूप में कॉल से जुड़ें',
    speakerIntro: 'आप स्पीकर हैं। आपकी आवाज़ रिसीवर के कंप्यूटर पर जाती है, जो कॉल में ठगी के तरीके जाँचता है। उस जाँच का कुछ भी इस फ़ोन पर नहीं दिखता।',
    codeInput: 'कॉल कोड (6 अंक)',
    codeInvalid: 'रिसीवर की स्क्रीन पर दिखा 6 अंकों का कोड लिखें।',
    speakerConsent: 'मैं सहमत हूँ कि मेरी आवाज़ रिसीवर के कंप्यूटर और स्पीच-टू-टेक्स्ट व विश्लेषण के लिए Gnani को भेजी जाए। मैं केवल अभिनय की हुई, काल्पनिक बातें बोलूँगा/बोलूँगी, असली निजी, बैंक या पहचान की जानकारी कभी नहीं।',
    join: 'कॉल से जुड़ें',
    connecting: 'जुड़ रहा है…',
    connected: 'जुड़ गए। अब आप बोल सकते हैं।',
    muted: 'म्यूट',
    mute: 'म्यूट करें',
    unmute: 'अनम्यूट करें',
    endCall: 'कॉल खत्म करें',
    ended: 'कॉल खत्म हो गई।',
    joinAnother: 'दूसरी कॉल से जुड़ें',
    micDenied: 'माइक्रोफ़ोन बंद है। ब्राउज़र की साइट सेटिंग में इसे अनुमति दें और फिर कोशिश करें।',
    keepScreenOn: 'कॉल के दौरान यह स्क्रीन चालू रखें, वरना फ़ोन आपकी आवाज़ भेजना बंद कर देता है।',
    lostConnection: 'कनेक्शन टूट गया।',
    roleSpeaker: 'स्पीकर',
    nothingShown: 'इस फ़ोन पर कोई विश्लेषण नहीं दिखता।',
    levelLabel: 'माइक्रोफ़ोन का स्तर',
    speakHint: 'बोलिए और पट्टी को हिलते देखिए।',
    silenceWarning: 'हमें आपकी आवाज़ नहीं आ रही। देखें कि म्यूट तो नहीं है, माइक्रोफ़ोन के पास आएँ, और माइक्रोफ़ोन की अनुमति दी गई हो।',
    reconnecting: 'कनेक्शन टूट गया। कॉल से दोबारा जुड़ने की कोशिश जारी है…',
    rejoinTitle: 'आपकी कॉल शायद अभी चल रही है',
    rejoinButton: 'कॉल से दोबारा जुड़ें',
    receiverReconnecting: (s) => `फ़ोन का कनेक्शन टूट गया। दोबारा जुड़ने के लिए ${s} सेकंड तक इंतज़ार…`,
    receivingAudio: 'फ़ोन से आवाज़ आ रही है',
    audioLevelLabel: 'आने वाली आवाज़ का स्तर',
    audioNone: 'फ़ोन से कोई आवाज़ नहीं आ रही।',
    audioSilent: 'फ़ोन चुप्पी भेज रहा है: वह म्यूट हो सकता है, या कोई बोल नहीं रहा।',
  },
  live: {
    title: 'लाइव जाँच',
    intro: 'कॉल को होते समय सुनें, या किसी रिकॉर्डिंग को लाइव की तरह चलाएँ। शब्द पहचाने जाते ही जोखिम मीटर बदलता है। इसका उपयोग केवल कॉल में शामिल सभी लोगों की अनुमति से करें।',
    micHint: 'आपका ब्राउज़र माइक्रोफ़ोन की अनुमति माँगेगा। यह पेज http://127.0.0.1:8000 या localhost पर खुला होना चाहिए।',
    startMic: 'सुनना शुरू करें (माइक्रोफ़ोन)',
    replay: 'रिकॉर्डिंग को लाइव कॉल की तरह चलाएँ',
    stop: 'रोकें और रिपोर्ट पाएँ',
    connecting: 'जुड़ रहा है…',
    listening: 'सुन रहा है…',
    stopping: 'पूरा करके रिपोर्ट सहेजी जा रही है…',
    meter: 'अब तक का जोखिम',
    alertHigh: 'चेतावनी: इस कॉल में ठगी के संकेत दिख रहे हैं। कोई कोड, पिन या पासवर्ड साझा न करें। कॉल काटें और अपने बैंक के आधिकारिक नंबर पर खुद कॉल करें।',
    alertElevated: 'सावधान: कोई संवेदनशील जानकारी माँगी जा रही है। कुछ भी बताने से पहले जाँचें कि माँगने वाला कौन है।',
    openReport: 'पूरी रिपोर्ट खोलें',
    again: 'दूसरी जाँच शुरू करें',
    limitReached: (n) => `${n} सेकंड की सीमा पूरी हो गई, इसलिए जाँच रोक दी गई।`,
    tooShort: 'कॉल इतनी छोटी थी कि जाँच नहीं हो सकी।',
    waiting: 'बोली का इंतज़ार…',
    spotted: 'अब तक मिले संकेत',
    warningNote: 'स्पीच पहचान स्ट्रीम में समस्या आई; जाँच जारी है।',
  },
  code: 'hi',
  appName: 'call-shield',
  tagline: 'किसी कॉल रिकॉर्डिंग में ठगी के तरीकों और नकली (सिंथेटिक) आवाज़ के संकेतों की जाँच करें।',
  privacy: 'विश्लेषण इसी कंप्यूटर पर चलता है। रिकॉर्डिंग सिर्फ़ स्थानीय डेटा फ़ोल्डर में रहती हैं और आप उन्हें यहीं से कभी भी हटा सकते हैं।',
  interfaceLanguage: 'इंटरफ़ेस की भाषा',
  uploadTitle: 'रिकॉर्डिंग जाँचें',
  chooseFile: 'ऑडियो फ़ाइल चुनें',
  dropHint: 'या यहाँ छोड़ें (WAV, MP3, M4A, FLAC या OGG)',
  noFile: 'कोई फ़ाइल नहीं चुनी',
  languageLabel: 'रिकॉर्डिंग में बोली गई भाषा',
  langs: { auto: 'पक्का नहीं (अंग्रेज़ी, हिंदी और मराठी तीनों में जाँच; लागत लगभग 3 गुना)', en: 'अंग्रेज़ी', hinglish: 'हिंग्लिश (हिंदी और अंग्रेज़ी मिली-जुली)', mr: 'मराठी', hi: 'हिंदी' },
  consent: 'इस रिकॉर्डिंग में मौजूद सभी लोगों से मुझे इसे जाँचने की अनुमति है। मैं समझता/समझती हूँ कि ऑडियो को टेक्स्ट में बदलने के लिए उसे Gnani की स्पीच सेवा को भेजा जाता है।',
  skipAudio: 'आवाज़ की जाँच छोड़ें (तेज़)',
  analyse: 'जाँचें',
  keyMissing: 'Gnani API कुंजी नहीं मिली, इसलिए ट्रांसक्रिप्शन विफल होगा। इसे .env फ़ाइल में जोड़ें और सर्वर फिर से शुरू करें।',
  tooBig: (mb) => `यह फ़ाइल ${mb} MB से बड़ी है।`,
  working: 'काम जारी है…',
  steps: { queued: 'प्रतीक्षा में', transcribing: 'Gnani से टेक्स्ट बनाया जा रहा है', analysing: 'ठगी के तरीके खोजे जा रहे हैं', checking_audio: 'आवाज़ की जाँच हो रही है' },
  failedTitle: 'जाँच विफल रही',
  back: 'वापस',
  newAnalysis: 'दूसरी रिकॉर्डिंग जाँचें',
  history: 'पिछली जाँचें',
  noHistory: 'अभी कुछ नहीं है।',
  open: 'खोलें',
  delete: 'हटाएँ',
  deleteAll: 'सब कुछ हटाएँ',
  confirmDelete: 'इस रिकॉर्डिंग और उसकी रिपोर्ट को हटाएँ?',
  confirmDeleteAll: 'सभी रिकॉर्डिंग और रिपोर्ट हटाएँ?',
  download: 'रिपोर्ट डाउनलोड करें (HTML)',
  levels: { high: 'ज़्यादा जोखिम', elevated: 'जाँच-परख ज़रूरी', low: 'ठगी के संकेत नहीं मिले' },
  plain: {
    high: 'इस कॉल में ठगी के कई संकेत दिखते हैं।',
    elevated: 'कोई संवेदनशील जानकारी माँगी जा रही है। कुछ भी बताने से पहले जाँचें कि माँगने वाला कौन है।',
    low: 'इस रिकॉर्डिंग में ठगी के कोई संकेत नहीं मिले।',
  },
  advice: {
    high: [
      'कोई कोड, पिन, पासवर्ड या भुगतान की जानकारी साझा न करें।',
      'कॉल काट दें। अपने कार्ड के पीछे छपे नंबर या बैंक की आधिकारिक वेबसाइट से बैंक को खुद कॉल करें।',
      'इस कॉलर के भेजे किसी लिंक पर क्लिक न करें और कोई ऐप इंस्टॉल न करें।',
      'अगर आप कुछ साझा कर चुके हैं, तो तुरंत बैंक को कॉल करके खाता या कार्ड ब्लॉक कराएँ। भारत में साइबर ठगी की शिकायत हेल्पलाइन 1930 या cybercrime.gov.in पर भी कर सकते हैं।',
    ],
    elevated: [
      'कोड सिर्फ़ उसी को बताएँ जिससे आपने खुद संपर्क किया हो और जिस पर आपको भरोसा हो।',
      'अगर पक्का न हो, तो कॉल काटकर आधिकारिक नंबर पर खुद कॉल करें।',
    ],
    low: ['यह फ़ैसले में मदद का औज़ार है, गारंटी नहीं। कुछ भी गड़बड़ लगे तो कॉल काटकर आधिकारिक नंबर पर कॉल करें।'],
  },
  whatToDo: 'अभी क्या करें',
  conversation: 'क्या कहा गया',
  authenticity: 'आवाज़ कैसी लगती है',
  evidence: 'सबूत',
  minor: 'छोटे संकेत',
  minorNote: 'ये अकेले जोखिम स्तर बढ़ाने के लिए काफ़ी नहीं हैं।',
  unreliable: 'भरोसे से जाँच नहीं हो सकी',
  unreliablePlain: 'ट्रांसक्रिप्ट आपकी चुनी हुई भाषा जैसा नहीं दिखता, इसलिए "ठगी के संकेत नहीं मिले" पर भरोसा नहीं किया जा सकता।',
  unreliableAdvice: [
    'इस जाँच को हटाएँ और सही भाषा चुनकर रिकॉर्डिंग फिर से अपलोड करें, या "पक्का नहीं" चुनें।',
    'अगर कॉल संदिग्ध लगी थी, तो उसे संदिग्ध ही मानें: कोई कोड साझा न करें और बैंक के आधिकारिक नंबर पर खुद कॉल करें।',
  ],
  languageWarning: {
    not_english: 'यह ट्रांसक्रिप्ट अंग्रेज़ी जैसा नहीं दिखता। अगर रिकॉर्डिंग किसी और भाषा में है, तो ठगी की जाँच में कुछ छूट सकता है।',
    not_devanagari: 'आपकी चुनी भाषा के लिए अपेक्षित देवनागरी लिपि में यह ट्रांसक्रिप्ट नहीं है। ठगी की जाँच में कुछ छूट सकता है।',
  },
  noEvidence: 'कोई संकेत नहीं मिला।',
  transcript: 'ट्रांसक्रिप्ट',
  transcriptHint: 'किसी हाइलाइट किए गए वाक्यांश पर टैप करें, पता चलेगा कि उसे क्यों चिह्नित किया गया।',
  legend: { request: 'माँग', pressure: 'दबाव', context: 'दावा या बहाना', warning: 'चेतावनी वाले शब्द' },
  spokenNumbers: 'बोले गए अंकों के क्रम',
  digitNote: 'बोले गए अंकों के क्रम सिर्फ़ संदर्भ के लिए दिखाए गए हैं और जोखिम स्तर नहीं बदलते। किसी अजनबी को कोड पढ़कर सुनाना ख़तरे का संकेत है।',
  digitsCount: (n) => `${n} अंक`,
  limitations: 'सीमाएँ',
  limits: [
    'ठगी वाले शब्दों की सूची शुरुआती मसौदा है; इसे अभी किसी मातृभाषी ने नहीं जाँचा है।',
    'ट्रांसक्रिप्ट स्पीच-टू-टेक्स्ट से बनता है; वहाँ की गलतियाँ ठगी वाले शब्द छिपा सकती हैं या गलत दिखा सकती हैं।',
    'बोलने वालों को अलग नहीं किया गया है, इसलिए रिपोर्ट यह नहीं बता सकती कि क्या किसने कहा।',
    'आवाज़ की जाँच एक छोटे पहले से प्रशिक्षित मॉडल से होती है, जो अनदेखे नकली ऑडियो पर कमज़ोर है (एक प्रकाशित वास्तविक-दुनिया परीक्षण में लगभग 44% त्रुटि)। इसका स्कोर अनिश्चित संकेत है, सबूत नहीं।',
    'आवाज़ की जाँच आधुनिक AI से बनी आवाज़ें पकड़ने में चूक सकती है, इसलिए "कोई संकेत नहीं मिला" का मतलब यह नहीं कि आवाज़ इंसान की है।',
    'असली इंसान भी ठगी कर सकता है और नकली आवाज़ भी हानिरहित बात कह सकती है। दोनों जाँचें एक-दूसरे से स्वतंत्र हैं।',
    'ऑडियो को टेक्स्ट बनाने के लिए Gnani की सेवा को भेजा गया था। केवल उन्हीं रिकॉर्डिंग की जाँच करें जिनके लिए बोलने वालों की सहमति हो।',
  ],
  auth: {
    natural: 'सिंथेटिक आवाज़ के संकेत नहीं मिले (कमज़ोर जाँच)',
    synthetic: 'सिंथेटिक जैसी (अंतरिम)',
    inconclusive_band: 'अनिर्णायक: स्कोर दोनों सीमाओं के बीच है',
    inconclusive_short: 'अनिर्णायक: बोलने का हिस्सा बहुत कम है',
    unavailable: 'उपलब्ध नहीं',
  },
  authNote: 'यह जाँच सिर्फ़ आवाज़ की बनावट देखती है। इससे यह साबित नहीं होता कि कॉल करने वाला असल में कौन है। आधुनिक AI (टेक्स्ट-टू-स्पीच) और क्लोन की गई आवाज़ें इसे आसानी से पार कर सकती हैं।',
  medianLine: (m, a, b, n) => `मध्यिका स्कोर ${m} (बीच का आधा हिस्सा ${a} से ${b}), लगभग 4 सेकंड की ${n} खिड़कियों पर।`,
  chartTitle: 'हर 4 सेकंड की खिड़की का स्कोर',
  bandNatural: 'प्राकृतिक',
  bandSynthetic: 'सिंथेटिक',
  provisional: 'सीमाएँ अंतरिम हैं और मूल्यांकन चरण में दोबारा तय की जाएँगी।',
  categories: {
    otp_request: { label: 'वन-टाइम कोड (OTP) माँगता है', explain: 'बैंक या असली सेवाओं को आपसे OTP पढ़कर सुनाने की ज़रूरत कभी नहीं पड़ती।' },
    credential_request: { label: 'पिन, पासवर्ड या कार्ड/पहचान नंबर माँगता है', explain: 'कोई भी असली व्यक्ति कॉल पर आपका पिन या पासवर्ड नहीं माँगता।' },
    payment_request: { label: 'पैसे या भुगतान की माँग', explain: 'पैसे, ट्रांसफ़र या पेमेंट लिंक की माँग करता है।' },
    remote_access: { label: 'रिमोट-कंट्रोल ऐप इंस्टॉल करने को कहता है', explain: 'रिमोट-कंट्रोल ऐप से कोई अजनबी आपका फ़ोन या कंप्यूटर चला सकता है।' },
    urgency: { label: 'जल्दबाज़ी करवाता है', explain: 'आपको तुरंत कदम उठाने के लिए धकेलता है ताकि आप रुककर सोच न सकें।' },
    threat: { label: 'नतीजे की धमकी देता है', explain: 'अकाउंट ब्लॉक होने, कानूनी कार्रवाई या कनेक्शन कटने की धमकी देकर डराता है।' },
    secrecy: { label: 'बात गुप्त रखने को कहता है', explain: 'आपको किसी से पूछने या जाँचने से रोकता है।' },
    verification_bypass: { label: 'जाँच करने से रोकता है', explain: 'आपको जाँच करने, कॉल काटने या सामान्य प्रक्रिया अपनाने से रोकता है।' },
    authority: { label: 'बैंक या अधिकारी होने का दावा', explain: 'ठग भरोसा जीतने के लिए अधिकार का दावा करते हैं।' },
    kyc_pretext: { label: 'KYC का बहाना', explain: 'KYC अपडेट बैंक ठगी की बहुत आम शुरुआत है।' },
    account_alert: { label: 'खाते में गड़बड़ी का दावा', explain: 'नकली फ्रॉड-विभाग की कॉल अक्सर संदिग्ध गतिविधि या अनधिकृत चार्ज से शुरू होती हैं, या रिफंड या इनाम का लालच देती हैं।' },
    warning_otp: { label: 'कोड साझा न करने की चेतावनी', explain: '"अपना OTP किसी को न बताएँ" जैसे सावधानी वाले शब्द। इसे माँग नहीं, चेतावनी माना जाता है।' },
    warning_cred: { label: 'पिन या पासवर्ड साझा न करने की चेतावनी', explain: 'सावधानी वाले शब्द। इसे माँग नहीं, चेतावनी माना जाता है।' },
  },
}

const mr: Dict = {
  speakers: {
    title: 'कोण काय म्हणाले',
    word: 'वक्ता',
    checkbox: 'ही दोन व्यक्तींमधील संभाषण आहे (वक्ते वेगळे करा)',
    hint: 'यासाठी विशिष्ट भाषा निवडावी लागते ("खात्री नाही" नाही) आणि जास्त वेळ लागतो. प्रत्येक व्यक्ती वेगळ्या स्टीरिओ चॅनेलवर असल्यास सर्वोत्तम चालते.',
    who: (label) => `फसवणुकीची चिन्हे ${label} कडून येत आहेत.`,
    nobody: 'कोणताही वक्ता संशयास्पद वाटला नाही.',
    noSigns: 'या वक्त्याकडून फसवणुकीची कोणतीही चिन्हे नाहीत.',
    voice: 'आवाजाची तपासणी',
    noteDiarization: 'वक्ते Gnani च्या वक्ता-ओळखीने (डायरायझेशन) वेगळे केले. ती आवाजांची अदलाबदल करू शकते.',
    noteChannels: 'वक्ते दोन स्टीरिओ चॅनेल वापरून वेगळे केले.',
    noteSingle: 'फक्त एकच वक्ता आढळला, त्यामुळे हे सामान्य तपासणीसारखेच आहे.',
  },
  alert: {
    headline: 'हा कॉल फसवणुकीसारखा वाटतो',
    subline: 'कोणताही कोड, पिन, पासवर्ड किंवा पेमेंटची माहिती सांगू नका.',
    elevated: 'सावध रहा: या कॉलमध्ये धोक्याची चिन्हे आहेत. तपासल्याशिवाय कोणताही कोड किंवा पैसे देऊ नका.',
    dismiss: 'समजले',
    repeat: 'पुन्हा सांगा',
    settings: 'अलर्ट सेटिंग',
    sound: 'बीप',
    voice: 'सल्ला मोठ्याने सांगा',
    fullscreen: 'पूर्ण स्क्रीन इशारा',
    echoNote: 'फोन त्याच खोलीत असेल तर तो बोललेला अलर्ट पकडू शकतो. हेडफोन वापरा, किंवा फोन दुसऱ्या खोलीत ठेवा.',
    noVoice: 'या डिव्हाइसवर या भाषेचा आवाज इन्स्टॉल केलेला नाही, म्हणून सल्ला फक्त स्क्रीनवर दिसेल.',
    heard: 'काय ऐकले गेले',
    spoken: 'सावधान. हा कॉल फसवणुकीसारखा वाटतो. कोणताही कोड किंवा पेमेंट तपशील सांगू नका. फोन कट करा आणि कार्डच्या मागे छापलेल्या नंबरवर बँकेला कॉल करा.',
    titleFlash: 'फसवणुकीचा इशारा',
  },
  nav: { upload: 'रेकॉर्डिंग अपलोड करा', live: 'लाइव तपासणी', call: 'कॉल स्वीकारा' },
  call: {
    nav: 'कॉल स्वीकारा',
    title: 'कॉल स्वीकारा',
    intro: 'कॉल सुरू करा, मग जो फोन स्पीकर होणार आहे त्यावर कोड स्कॅन करा किंवा पत्ता उघडा. हा संगणक रिसीव्हर आहे: तो कॉल ऐकतो आणि लाइव तपासणी दाखवतो. फक्त अभिनय केलेले, काल्पनिक बोलणे वापरा, खरी वैयक्तिक, बँक किंवा ओळखीची माहिती कधीही नको.',
    publicLabel: 'सार्वजनिक पत्ता (टनेल विंडोमधून)',
    publicHint: 'आधी टनेल सुरू करा (tools\\start_demo.bat). पत्ता असा दिसतो: https://something.trycloudflare.com',
    noTunnel: 'अजून टनेलचा पत्ता नाही, त्यामुळे फोन जोडला जाऊ शकत नाही. याच संगणकावर दुसऱ्या ब्राउझर टॅबमधून तुम्ही चाचणी करू शकता.',
    consent: 'मला समजते की स्पीकरचा आवाज त्याच्या फोनवरून या संगणकावर आणि नंतर ट्रान्सक्रिप्शनसाठी Gnani ला पाठवला जातो, आणि कॉलमधील सर्वांनी संमती दिली आहे. फक्त अभिनय केलेले, काल्पनिक बोलणे वापरले जाईल.',
    start: 'कॉल सुरू करा',
    cancel: 'कॉल रद्द करा',
    end: 'कॉल संपवा आणि अहवाल मिळवा',
    codeLabel: 'कॉल कोड',
    scan: 'फोनवर: हा कोड स्कॅन करा, किंवा खालील पत्ता उघडून कोड टाका.',
    joinAddress: 'जोडण्याचा पत्ता',
    waitingSpeaker: 'स्पीकर जोडला जाण्याची वाट पाहत आहे…',
    speakerJoined: 'स्पीकर जोडला गेला आहे आणि संमतीची खात्री करत आहे…',
    listen: 'या डिव्हाइसवर कॉल ऐका',
    listenHint: 'सुरुवातीला बंद असते. हेडफोन वापरा, किंवा फोन दुसऱ्या खोलीत ठेवा, नाहीतर फोन या संगणकाचा आवाज पकडून प्रतिध्वनी तयार करेल.',
    expires: (m) => `कोड एकदाच आणि ${m} मिनिटांसाठी चालतो.`,
    speakerTitle: 'स्पीकर म्हणून कॉलमध्ये जोडा',
    speakerIntro: 'तुम्ही स्पीकर आहात. तुमचा आवाज रिसीव्हरच्या संगणकावर जातो, जो कॉलमध्ये फसवणुकीचे डावपेच तपासतो. त्या तपासणीतले काहीही या फोनवर दिसत नाही.',
    codeInput: 'कॉल कोड (6 अंक)',
    codeInvalid: 'रिसीव्हरच्या स्क्रीनवर दिसणारा 6 अंकी कोड टाका.',
    speakerConsent: 'माझा आवाज रिसीव्हरच्या संगणकावर आणि स्पीच-टू-टेक्स्ट व विश्लेषणासाठी Gnani ला पाठवला जाण्यास माझी संमती आहे. मी फक्त अभिनय केलेले, काल्पनिक बोलेन, खरी वैयक्तिक, बँक किंवा ओळखीची माहिती कधीही नाही.',
    join: 'कॉलमध्ये जोडा',
    connecting: 'जोडत आहे…',
    connected: 'जोडले गेले. आता तुम्ही बोलू शकता.',
    muted: 'म्यूट',
    mute: 'म्यूट करा',
    unmute: 'अनम्यूट करा',
    endCall: 'कॉल संपवा',
    ended: 'कॉल संपला आहे.',
    joinAnother: 'दुसऱ्या कॉलमध्ये जोडा',
    micDenied: 'मायक्रोफोन बंद आहे. ब्राउझरच्या साइट सेटिंगमध्ये त्याला परवानगी द्या आणि पुन्हा प्रयत्न करा.',
    keepScreenOn: 'कॉल सुरू असताना ही स्क्रीन चालू ठेवा, नाहीतर फोन तुमचा आवाज पाठवणे थांबवतो.',
    lostConnection: 'कनेक्शन तुटले.',
    roleSpeaker: 'स्पीकर',
    nothingShown: 'या फोनवर कोणतेही विश्लेषण दिसत नाही.',
    levelLabel: 'मायक्रोफोनची पातळी',
    speakHint: 'बोला आणि पट्टी हलताना पहा.',
    silenceWarning: 'आम्हाला तुमचा आवाज ऐकू येत नाही. म्यूट नाही ना ते पहा, मायक्रोफोनच्या जवळ या, आणि मायक्रोफोनला परवानगी दिलेली असावी.',
    reconnecting: 'कनेक्शन तुटले. कॉलमध्ये पुन्हा जोडण्याचा प्रयत्न सुरू आहे…',
    rejoinTitle: 'तुमचा कॉल कदाचित अजून सुरू आहे',
    rejoinButton: 'कॉलमध्ये पुन्हा जोडा',
    receiverReconnecting: (s) => `फोनचे कनेक्शन तुटले. पुन्हा जोडण्यासाठी ${s} सेकंदांपर्यंत वाट पाहत आहे…`,
    receivingAudio: 'फोनवरून आवाज येत आहे',
    audioLevelLabel: 'येणाऱ्या आवाजाची पातळी',
    audioNone: 'फोनवरून कोणताही आवाज येत नाही.',
    audioSilent: 'फोन शांतता पाठवत आहे: तो म्यूट असू शकतो, किंवा कोणी बोलत नाही.',
  },
  live: {
    title: 'लाइव तपासणी',
    intro: 'कॉल सुरू असताना ऐका, किंवा एखादे रेकॉर्डिंग लाइव असल्यासारखे चालवा. शब्द ओळखले जाताच धोक्याचे मीटर बदलते. हे फक्त कॉलवरील सर्वांच्या परवानगीनेच वापरा.',
    micHint: 'तुमचा ब्राउझर मायक्रोफोनची परवानगी मागेल. हे पेज http://127.0.0.1:8000 किंवा localhost वर उघडलेले असावे.',
    startMic: 'ऐकायला सुरुवात करा (मायक्रोफोन)',
    replay: 'रेकॉर्डिंग लाइव कॉलसारखे चालवा',
    stop: 'थांबवा आणि अहवाल मिळवा',
    connecting: 'जोडले जात आहे…',
    listening: 'ऐकत आहे…',
    stopping: 'पूर्ण करून अहवाल जतन केला जात आहे…',
    meter: 'आतापर्यंतचा धोका',
    alertHigh: 'इशारा: या कॉलमध्ये फसवणुकीची चिन्हे दिसत आहेत. कोणताही कोड, पिन किंवा पासवर्ड सांगू नका. कॉल कट करा आणि बँकेच्या अधिकृत क्रमांकावर स्वतः कॉल करा.',
    alertElevated: 'काळजी घ्या: कोणतीतरी संवेदनशील माहिती मागितली जात आहे. काहीही सांगण्यापूर्वी मागणारा खरोखर कोण आहे ते तपासा.',
    openReport: 'संपूर्ण अहवाल उघडा',
    again: 'दुसरी तपासणी सुरू करा',
    limitReached: (n) => `${n} सेकंदांची मर्यादा गाठली, म्हणून तपासणी थांबवली.`,
    tooShort: 'कॉल इतका छोटा होता की तपासणी करता आली नाही.',
    waiting: 'बोलण्याची वाट पाहत आहे…',
    spotted: 'आतापर्यंत आढळलेली चिन्हे',
    warningNote: 'स्पीच ओळख प्रवाहात समस्या आली; तपासणी सुरू आहे.',
  },
  code: 'mr',
  appName: 'call-shield',
  tagline: 'कॉल रेकॉर्डिंगमध्ये फसवणुकीच्या पद्धती आणि कृत्रिम (सिंथेटिक) आवाजाची चिन्हे तपासा.',
  privacy: 'विश्लेषण याच संगणकावर होते. रेकॉर्डिंग फक्त स्थानिक डेटा फोल्डरमध्ये राहतात आणि तुम्ही त्या इथून कधीही हटवू शकता.',
  interfaceLanguage: 'इंटरफेसची भाषा',
  uploadTitle: 'रेकॉर्डिंग तपासा',
  chooseFile: 'ऑडिओ फाइल निवडा',
  dropHint: 'किंवा इथे टाका (WAV, MP3, M4A, FLAC किंवा OGG)',
  noFile: 'कोणतीही फाइल निवडलेली नाही',
  languageLabel: 'रेकॉर्डिंगमध्ये बोलली गेलेली भाषा',
  langs: { auto: 'खात्री नाही (इंग्रजी, हिंदी आणि मराठी तिन्हीत तपासते; खर्च सुमारे 3 पट)', en: 'इंग्रजी', hinglish: 'हिंग्लिश (हिंदी आणि इंग्रजी मिश्र)', mr: 'मराठी', hi: 'हिंदी' },
  consent: 'या रेकॉर्डिंगमधील सर्व व्यक्तींची मला ते तपासण्याची परवानगी आहे. ऑडिओचे मजकुरात रूपांतर करण्यासाठी तो Gnani च्या स्पीच सेवेकडे पाठवला जातो हे मला समजले आहे.',
  skipAudio: 'आवाजाची तपासणी वगळा (जलद)',
  analyse: 'तपासा',
  keyMissing: 'Gnani API की सापडली नाही, त्यामुळे ट्रान्सक्रिप्शन अयशस्वी होईल. ती .env फाइलमध्ये टाका आणि सर्व्हर पुन्हा सुरू करा.',
  tooBig: (mb) => `ही फाइल ${mb} MB पेक्षा मोठी आहे.`,
  working: 'काम सुरू आहे…',
  steps: { queued: 'प्रतीक्षेत', transcribing: 'Gnani द्वारे मजकूर तयार होत आहे', analysing: 'फसवणुकीच्या पद्धती शोधल्या जात आहेत', checking_audio: 'आवाज तपासला जात आहे' },
  failedTitle: 'तपासणी अयशस्वी झाली',
  back: 'मागे',
  newAnalysis: 'दुसरे रेकॉर्डिंग तपासा',
  history: 'आधीच्या तपासण्या',
  noHistory: 'अजून काहीही नाही.',
  open: 'उघडा',
  delete: 'हटवा',
  deleteAll: 'सर्व काही हटवा',
  confirmDelete: 'हे रेकॉर्डिंग आणि त्याचा अहवाल हटवायचा?',
  confirmDeleteAll: 'सर्व रेकॉर्डिंग आणि अहवाल हटवायचे?',
  download: 'अहवाल डाउनलोड करा (HTML)',
  levels: { high: 'जास्त धोका', elevated: 'तपासून पाहणे आवश्यक', low: 'फसवणुकीची चिन्हे आढळली नाहीत' },
  plain: {
    high: 'या कॉलमध्ये फसवणुकीची अनेक चिन्हे दिसतात.',
    elevated: 'कोणतीतरी संवेदनशील माहिती मागितली जात आहे. काहीही सांगण्यापूर्वी मागणारा खरोखर कोण आहे ते तपासा.',
    low: 'या रेकॉर्डिंगमध्ये फसवणुकीची कोणतीही चिन्हे आढळली नाहीत.',
  },
  advice: {
    high: [
      'कोणताही कोड, पिन, पासवर्ड किंवा पेमेंटची माहिती सांगू नका.',
      'कॉल कट करा. तुमच्या कार्डच्या मागे छापलेल्या क्रमांकावर किंवा बँकेच्या अधिकृत वेबसाइटवरून बँकेला स्वतः कॉल करा.',
      'या कॉलरने पाठवलेल्या कोणत्याही लिंकवर क्लिक करू नका आणि कोणतेही अ‍ॅप इन्स्टॉल करू नका.',
      'तुम्ही काही माहिती आधीच दिली असल्यास, लगेच बँकेला कॉल करून खाते किंवा कार्ड ब्लॉक करा. भारतात सायबर फसवणुकीची तक्रार हेल्पलाइन 1930 वर किंवा cybercrime.gov.in वर करता येते.',
    ],
    elevated: [
      'कोड फक्त अशा व्यक्तीला सांगा जिच्याशी तुम्ही स्वतः संपर्क साधला आहे आणि जिच्यावर तुमचा विश्वास आहे.',
      'खात्री नसल्यास कॉल कट करून अधिकृत क्रमांकावर स्वतः कॉल करा.',
    ],
    low: ['हे निर्णय घेण्यासाठी मदत करणारे साधन आहे, हमी नाही. काहीही खटकल्यास कॉल कट करून अधिकृत क्रमांकावर कॉल करा.'],
  },
  whatToDo: 'आता काय करावे',
  conversation: 'काय बोलले गेले',
  authenticity: 'आवाज कसा वाटतो',
  evidence: 'पुरावा',
  minor: 'किरकोळ चिन्हे',
  minorNote: 'ही एकटी धोक्याची पातळी वाढवण्यासाठी पुरेशी नाहीत.',
  unreliable: 'विश्वासार्हपणे तपासता आले नाही',
  unreliablePlain: 'ट्रान्सक्रिप्ट तुम्ही निवडलेल्या भाषेसारखे दिसत नाही, त्यामुळे "फसवणुकीची चिन्हे आढळली नाहीत" यावर विश्वास ठेवता येत नाही.',
  unreliableAdvice: [
    'ही तपासणी हटवा आणि योग्य भाषा निवडून रेकॉर्डिंग पुन्हा अपलोड करा, किंवा "खात्री नाही" निवडा.',
    'कॉल संशयास्पद वाटला असेल तर तो संशयास्पदच माना: कोणताही कोड सांगू नका आणि बँकेच्या अधिकृत क्रमांकावर स्वतः कॉल करा.',
  ],
  languageWarning: {
    not_english: 'हे ट्रान्सक्रिप्ट इंग्रजीसारखे दिसत नाही. रेकॉर्डिंग दुसऱ्या भाषेत असल्यास फसवणुकीच्या तपासणीत काही सुटू शकते.',
    not_devanagari: 'तुम्ही निवडलेल्या भाषेसाठी अपेक्षित असलेल्या देवनागरी लिपीत हे ट्रान्सक्रिप्ट नाही. फसवणुकीच्या तपासणीत काही सुटू शकते.',
  },
  noEvidence: 'कोणतीही चिन्हे आढळली नाहीत.',
  transcript: 'ट्रान्सक्रिप्ट',
  transcriptHint: 'हायलाइट केलेल्या शब्दसमूहावर टॅप करा, तो का चिन्हांकित केला ते कळेल.',
  legend: { request: 'मागणी', pressure: 'दबाव', context: 'दावा किंवा बहाणा', warning: 'सावधगिरीचे शब्द' },
  spokenNumbers: 'बोललेल्या अंकांचे क्रम',
  digitNote: 'बोललेल्या अंकांचे क्रम फक्त संदर्भासाठी दाखवले आहेत आणि धोक्याची पातळी बदलत नाहीत. अनोळखी व्यक्तीला कोड वाचून दाखवणे हे धोक्याचे चिन्ह आहे.',
  digitsCount: (n) => `${n} अंक`,
  limitations: 'मर्यादा',
  limits: [
    'फसवणुकीच्या शब्दांची यादी हा सुरुवातीचा मसुदा आहे; तो अजून कोणत्याही मातृभाषकाने तपासलेला नाही.',
    'ट्रान्सक्रिप्ट स्पीच-टू-टेक्स्टमधून तयार होते; तिथल्या चुका फसवणुकीचे शब्द लपवू शकतात किंवा चुकीचे दाखवू शकतात.',
    'बोलणारे वेगळे केलेले नाहीत, त्यामुळे अहवाल कोण काय म्हणाले ते सांगू शकत नाही.',
    'आवाजाची तपासणी एका लहान, आधीच प्रशिक्षित मॉडेलने होते, जे न पाहिलेल्या खोट्या ऑडिओवर कमकुवत आहे (एका प्रकाशित वास्तव-जगातील चाचणीत सुमारे 44% त्रुटी). त्याचा स्कोअर अनिश्चित संकेत आहे, पुरावा नाही.',
    'आवाजाची तपासणी आधुनिक AI ने बनवलेले आवाज ओळखण्यात चुकू शकते, म्हणून "कोणतीही चिन्हे आढळली नाहीत" याचा अर्थ आवाज माणसाचा आहे असा नाही.',
    'खरी व्यक्तीही फसवणूक करू शकते आणि कृत्रिम आवाजही निरुपद्रवी गोष्ट बोलू शकतो. दोन्ही तपासण्या एकमेकांपासून स्वतंत्र आहेत.',
    'ऑडिओचे मजकुरात रूपांतर करण्यासाठी तो Gnani च्या सेवेकडे पाठवला गेला होता. फक्त ज्यांची बोलणाऱ्यांनी संमती दिली आहे अशाच रेकॉर्डिंग तपासा.',
  ],
  auth: {
    natural: 'कृत्रिम आवाजाची चिन्हे आढळली नाहीत (कमकुवत तपासणी)',
    synthetic: 'कृत्रिम आवाजासारखा (तात्पुरता)',
    inconclusive_band: 'अनिर्णायक: स्कोअर दोन्ही मर्यादांच्या मध्ये आहे',
    inconclusive_short: 'अनिर्णायक: बोलण्याचा भाग खूप कमी आहे',
    unavailable: 'उपलब्ध नाही',
  },
  authNote: 'ही तपासणी फक्त आवाजाची रचना पाहते. कॉल करणारा प्रत्यक्षात कोण आहे हे यातून सिद्ध होत नाही. आधुनिक AI (टेक्स्ट-टू-स्पीच) आणि क्लोन केलेले आवाज ही तपासणी सहज पार करू शकतात.',
  medianLine: (m, a, b, n) => `मध्यक स्कोअर ${m} (मधला अर्धा भाग ${a} ते ${b}), सुमारे 4 सेकंदांच्या ${n} खिडक्यांवर.`,
  chartTitle: 'प्रत्येक 4 सेकंदांच्या खिडकीचा स्कोअर',
  bandNatural: 'नैसर्गिक',
  bandSynthetic: 'कृत्रिम',
  provisional: 'मर्यादा तात्पुरत्या आहेत आणि मूल्यांकन टप्प्यात पुन्हा ठरवल्या जातील.',
  categories: {
    otp_request: { label: 'वन-टाइम कोड (OTP) मागतो', explain: 'बँका किंवा खऱ्या सेवांना तुमच्याकडून OTP वाचून घेण्याची गरज कधीच पडत नाही.' },
    credential_request: { label: 'पिन, पासवर्ड किंवा कार्ड/ओळख क्रमांक मागतो', explain: 'कोणतीही खरी व्यक्ती कॉलवर तुमचा पिन किंवा पासवर्ड मागत नाही.' },
    payment_request: { label: 'पैसे किंवा पेमेंटची मागणी', explain: 'पैसे, ट्रान्सफर किंवा पेमेंट लिंकची मागणी करतो.' },
    remote_access: { label: 'रिमोट-कंट्रोल अ‍ॅप इन्स्टॉल करायला सांगतो', explain: 'रिमोट-कंट्रोल अ‍ॅपमुळे एखादी अनोळखी व्यक्ती तुमचा फोन किंवा संगणक चालवू शकते.' },
    urgency: { label: 'घाई करायला लावतो', explain: 'तुम्ही थांबून विचार करू नये म्हणून लगेच कृती करायला भाग पाडतो.' },
    threat: { label: 'परिणामांची धमकी देतो', explain: 'खाते ब्लॉक होणे, कायदेशीर कारवाई किंवा कनेक्शन तोडले जाणे अशा धमक्या देऊन घाबरवतो.' },
    secrecy: { label: 'गोष्ट गुप्त ठेवायला सांगतो', explain: 'तुम्हाला कोणाला विचारण्यापासून किंवा तपासण्यापासून रोखतो.' },
    verification_bypass: { label: 'तपासणी करण्यापासून रोखतो', explain: 'तुम्हाला तपासणी करण्यापासून, कॉल कट करण्यापासून किंवा नेहमीची प्रक्रिया पाळण्यापासून परावृत्त करतो.' },
    authority: { label: 'बँक किंवा अधिकारी असल्याचा दावा', explain: 'फसवणूक करणारे विश्वास जिंकण्यासाठी अधिकाराचा दावा करतात.' },
    kyc_pretext: { label: 'केवायसीचा बहाणा', explain: 'केवायसी अपडेट ही बँक फसवणुकीची अतिशय सामान्य सुरुवात आहे.' },
    account_alert: { label: 'खात्यात गडबड असल्याचा दावा', explain: 'खोट्या फसवणूक-विभागाचे कॉल अनेकदा संशयास्पद व्यवहार किंवा अनधिकृत शुल्कापासून सुरू होतात, किंवा परताव्याचे किंवा बक्षिसाचे आमिष दाखवतात.' },
    warning_otp: { label: 'कोड सांगू नका अशी सूचना', explain: '"तुमचा OTP कोणालाही सांगू नका" अशा सावधगिरीच्या शब्दांना मागणी नव्हे, तर सूचना मानले जाते.' },
    warning_cred: { label: 'पिन किंवा पासवर्ड सांगू नका अशी सूचना', explain: 'सावधगिरीचे शब्द. त्यांना मागणी नव्हे, तर सूचना मानले जाते.' },
  },
}

export const STRINGS: Record<Lang, Dict> = { en, hi, mr }
export const LANG_NAMES: Record<Lang, string> = { en: 'English', hi: 'हिंदी', mr: 'मराठी' }

export function categoryText(t: Dict, category: string, fallbackExplain = ''): CategoryText {
  return t.categories[category] ?? { label: category.replace(/_/g, ' '), explain: fallbackExplain }
}

/** The server labels speakers "Speaker 1", "Speaker 2": show them in the interface language. */
export function speakerName(t: Dict, label: string): string {
  const m = /^Speaker (\d+)$/.exec(label)
  return m ? `${t.speakers.word} ${m[1]}` : label
}
