import type { Lang } from '../types'
import type { Source } from './types'

export interface QuickInfo { duration: string; level: string; firstAlert: string | null; tactics: string[] }

export interface ReportText {
  levelShort: Record<'low' | 'elevated' | 'high', string>
  title: string; back: string; technical: string; print: string; exportJson: string; delete: string; deleteConfirm: string; language: string
  verdict: string; duration: string; firstAlert: string; highAt: string; tactics: string; modelPeak: string; voice: string; none: string; notReached: string
  quickTitle: string; quick: (q: QuickInfo) => string
  timelineTitle: string; chartTitle: string; chartHelp: string; replay: string; pause: string; restart: string; speed: string; showAll: string
  cursorAt: (t: string) => string
  filtersTitle: string; searchLabel: string; searchPlaceholder: string; allTactics: string
  sources: Record<Source, string>
  eventsTitle: string; callTime: string; clockTime: string; noEvents: string
  transcriptTitle: string; track: string; noTranscript: string; timesNote: string; maskedNote: string
  ev: {
    callStarted: string; firstWords: string; joined: string; dropped: string; rejoined: string; listenOn: string; listenOff: string; ended: string
    warning: string; voice: string
    level: (from: string, to: string, by: string) => string; model: (pct: number) => string; alert: (level: string) => string
  }
  ai: {
    title: string; notSet: string; howTo: string; consent: (to: string) => string; auto: string; write: string; writing: string; again: string
    by: (model: string) => string; fellBack: (n: number) => string; warn: string; happened: string; why: string; advice: string; quotes: string; langNote: string
  }
  loading: string; loadError: string; noTimeline: string
}

const en: ReportText = {
  levelShort: { low: 'low', elevated: 'elevated', high: 'high' },
  title: 'Call report', back: 'Back', technical: 'Technical report', print: 'Print / save as PDF', exportJson: 'Download JSON', delete: 'Delete this report',
  deleteConfirm: 'Delete this report and its recording permanently?', language: 'Report language',
  verdict: 'Verdict', duration: 'Duration', firstAlert: 'First alert at', highAt: 'High alert at', tactics: 'Tactics heard', modelPeak: 'Model second opinion (peak)',
  voice: 'Voice check', none: 'None', notReached: 'Not reached',
  quickTitle: 'Quick summary',
  quick: (q) => `This ${q.duration} call ended at ${q.level} risk. ${q.firstAlert ? `The first alert came at ${q.firstAlert}.` : 'No alert was raised.'} ` +
    (q.tactics.length ? `Tactics heard: ${q.tactics.join(', ')}.` : 'No scam tactics were heard.'),
  timelineTitle: 'Timeline', chartTitle: 'Risk over time',
  chartHelp: 'Click or drag on the chart, or use the arrow keys, to move through the call. The dots below the line are events.',
  replay: 'Replay', pause: 'Pause', restart: 'Restart', speed: 'Speed', showAll: 'Show everything', cursorAt: (t) => `Showing the call up to ${t}`,
  filtersTitle: 'Filter', searchLabel: 'Search', searchPlaceholder: 'Search words or events', allTactics: 'All events',
  sources: { rules: 'Rules', model: 'Model', alert: 'Alerts', connection: 'Connection', voice: 'Voice check', system: 'System' },
  eventsTitle: 'What happened, step by step', callTime: 'Call time', clockTime: 'Clock time', noEvents: 'No events match.',
  transcriptTitle: 'What was said', track: 'Transcript', noTranscript: 'No words were transcribed.',
  timesNote: 'Times are when the app received the words. The speech-to-text service can deliver them a second or two after they were spoken.',
  maskedNote: 'Spoken digits are hidden (shown as •) in this report.',
  ev: {
    callStarted: 'The check started', firstWords: 'The first words were heard', joined: 'The phone joined the call', dropped: 'The phone connection dropped',
    rejoined: 'The phone reconnected', listenOn: 'Listening in switched on', listenOff: 'Listening in switched off', ended: 'The call ended',
    warning: 'The speech-to-text service reported a problem', voice: 'Voice check finished',
    level: (f, to, by) => `Risk changed from ${f} to ${to} (${by})`, model: (p) => `The language model rated the call ${p}% scam-like`, alert: (l) => `Alert shown: ${l}`,
  },
  ai: {
    title: 'AI-written summary', notSet: 'No AI service is set up yet, so only the quick summary is shown.',
    howTo: 'To turn it on, add the keys to the .env file (see .env.example) and restart the server.',
    consent: (to) => `Send the call text (digits hidden, no audio) to ${to} to write this summary`, auto: 'Write it automatically for every call',
    write: 'Write the AI summary', writing: 'Writing the summary…', again: 'Write again', by: (m) => `Written by the open model ${m}`, fellBack: (n) => `${n} other free model${n === 1 ? ' was' : 's were'} unavailable or unusable first.`,
    warn: 'AI-written text can contain mistakes. The verdict, the timeline and the highlighted words come from the rules, not from the AI.',
    happened: 'What happened', why: 'Why it looked risky', advice: 'What to do', quotes: 'Words quoted', langNote: 'Summary language',
  },
  loading: 'Loading the report…', loadError: 'The report could not be loaded.', noTimeline: 'This analysis has no timeline. Only live calls record one.',
}

const hi: ReportText = {
  levelShort: { low: 'कम', elevated: 'मध्यम', high: 'ऊँचे' },
  title: 'कॉल रिपोर्ट', back: 'वापस', technical: 'तकनीकी रिपोर्ट', print: 'प्रिंट / PDF सहेजें', exportJson: 'JSON डाउनलोड करें', delete: 'यह रिपोर्ट हटाएँ',
  deleteConfirm: 'यह रिपोर्ट और इसकी रिकॉर्डिंग हमेशा के लिए हटाएँ?', language: 'रिपोर्ट की भाषा',
  verdict: 'नतीजा', duration: 'अवधि', firstAlert: 'पहला अलर्ट', highAt: 'ऊँचा अलर्ट', tactics: 'सुनी गई चालें', modelPeak: 'मॉडल की दूसरी राय (सबसे ऊँची)',
  voice: 'आवाज़ की जाँच', none: 'कोई नहीं', notReached: 'नहीं हुआ',
  quickTitle: 'संक्षिप्त सारांश',
  quick: (q) => `यह ${q.duration} की कॉल ${q.level} जोखिम पर खत्म हुई। ${q.firstAlert ? `पहला अलर्ट ${q.firstAlert} पर आया।` : 'कोई अलर्ट नहीं आया।'} ` +
    (q.tactics.length ? `सुनी गई चालें: ${q.tactics.join(', ')}।` : 'कोई स्कैम वाली चाल नहीं सुनी गई।'),
  timelineTitle: 'समय-रेखा', chartTitle: 'समय के साथ जोखिम',
  chartHelp: 'कॉल में आगे-पीछे जाने के लिए चार्ट पर क्लिक करें या खींचें, या तीर वाले कीबोर्ड बटन दबाएँ। रेखा के नीचे के बिंदु घटनाएँ हैं।',
  replay: 'दोबारा चलाएँ', pause: 'रोकें', restart: 'फिर से शुरू', speed: 'गति', showAll: 'सब कुछ दिखाएँ', cursorAt: (t) => `कॉल ${t} तक दिखाई जा रही है`,
  filtersTitle: 'फ़िल्टर', searchLabel: 'खोजें', searchPlaceholder: 'शब्द या घटना खोजें', allTactics: 'सभी घटनाएँ',
  sources: { rules: 'नियम', model: 'मॉडल', alert: 'अलर्ट', connection: 'कनेक्शन', voice: 'आवाज़ की जाँच', system: 'सिस्टम' },
  eventsTitle: 'क्या हुआ, कदम दर कदम', callTime: 'कॉल का समय', clockTime: 'घड़ी का समय', noEvents: 'कोई घटना नहीं मिली।',
  transcriptTitle: 'क्या कहा गया', track: 'ट्रांसक्रिप्ट', noTranscript: 'कोई शब्द ट्रांसक्राइब नहीं हुए।',
  timesNote: 'समय वह है जब ऐप को शब्द मिले। स्पीच-टू-टेक्स्ट सेवा उन्हें बोले जाने के एक-दो सेकंड बाद दे सकती है।',
  maskedNote: 'इस रिपोर्ट में बोले गए अंक छिपाए गए हैं (• से दिखते हैं)।',
  ev: {
    callStarted: 'जाँच शुरू हुई', firstWords: 'पहले शब्द सुने गए', joined: 'फ़ोन कॉल से जुड़ा', dropped: 'फ़ोन का कनेक्शन टूट गया',
    rejoined: 'फ़ोन दोबारा जुड़ा', listenOn: 'सुनना चालू किया गया', listenOff: 'सुनना बंद किया गया', ended: 'कॉल खत्म हुई',
    warning: 'स्पीच-टू-टेक्स्ट सेवा ने समस्या बताई', voice: 'आवाज़ की जाँच पूरी हुई',
    level: (f, to, by) => `जोखिम ${f} से ${to} हुआ (${by})`, model: (p) => `भाषा मॉडल ने कॉल को ${p}% स्कैम जैसा आँका`, alert: (l) => `अलर्ट दिखाया गया: ${l}`,
  },
  ai: {
    title: 'AI द्वारा लिखा सारांश', notSet: 'अभी कोई AI सेवा चालू नहीं है, इसलिए केवल संक्षिप्त सारांश दिख रहा है।',
    howTo: 'इसे चालू करने के लिए .env फ़ाइल में कुंजियाँ जोड़ें (.env.example देखें) और सर्वर फिर से चालू करें।',
    consent: (to) => `यह सारांश लिखने के लिए कॉल का टेक्स्ट (अंक छिपे हुए, कोई ऑडियो नहीं) ${to} को भेजें`, auto: 'हर कॉल के लिए अपने-आप लिखें',
    write: 'AI सारांश लिखें', writing: 'सारांश लिखा जा रहा है…', again: 'फिर से लिखें', by: (m) => `ओपन मॉडल ${m} द्वारा लिखा गया`, fellBack: (n) => `पहले ${n} अन्य मुफ़्त मॉडल उपलब्ध या उपयोगी नहीं थे।`,
    warn: 'AI का लिखा टेक्स्ट गलत हो सकता है। नतीजा, समय-रेखा और चिह्नित शब्द नियमों से आते हैं, AI से नहीं।',
    happened: 'क्या हुआ', why: 'यह जोखिम भरा क्यों लगा', advice: 'क्या करें', quotes: 'उद्धृत शब्द', langNote: 'सारांश की भाषा',
  },
  loading: 'रिपोर्ट लोड हो रही है…', loadError: 'रिपोर्ट लोड नहीं हो सकी।', noTimeline: 'इस विश्लेषण की समय-रेखा नहीं है। केवल लाइव कॉल की समय-रेखा बनती है।',
}

const mr: ReportText = {
  levelShort: { low: 'कमी', elevated: 'मध्यम', high: 'उच्च' },
  title: 'कॉल अहवाल', back: 'मागे', technical: 'तांत्रिक अहवाल', print: 'प्रिंट / PDF म्हणून जतन करा', exportJson: 'JSON डाउनलोड करा', delete: 'हा अहवाल हटवा',
  deleteConfirm: 'हा अहवाल आणि त्याचे रेकॉर्डिंग कायमचे हटवायचे?', language: 'अहवालाची भाषा',
  verdict: 'निकाल', duration: 'कालावधी', firstAlert: 'पहिला अलर्ट', highAt: 'उच्च अलर्ट', tactics: 'ऐकलेल्या युक्त्या', modelPeak: 'मॉडेलचे दुसरे मत (सर्वोच्च)',
  voice: 'आवाजाची तपासणी', none: 'काहीही नाही', notReached: 'झाले नाही',
  quickTitle: 'थोडक्यात सारांश',
  quick: (q) => `हा ${q.duration} चा कॉल ${q.level} धोक्यावर संपला. ${q.firstAlert ? `पहिला अलर्ट ${q.firstAlert} वाजता आला.` : 'कोणताही अलर्ट आला नाही.'} ` +
    (q.tactics.length ? `ऐकलेल्या युक्त्या: ${q.tactics.join(', ')}.` : 'फसवणुकीची कोणतीही युक्ती ऐकू आली नाही.'),
  timelineTitle: 'कालरेषा', chartTitle: 'वेळेनुसार धोका',
  chartHelp: 'कॉलमध्ये पुढे-मागे जाण्यासाठी चार्टवर क्लिक करा किंवा ओढा, किंवा बाण कळा वापरा. रेषेखालील ठिपके म्हणजे घटना.',
  replay: 'पुन्हा चालवा', pause: 'थांबवा', restart: 'पुन्हा सुरू करा', speed: 'वेग', showAll: 'सर्व दाखवा', cursorAt: (t) => `कॉल ${t} पर्यंत दाखवला आहे`,
  filtersTitle: 'फिल्टर', searchLabel: 'शोधा', searchPlaceholder: 'शब्द किंवा घटना शोधा', allTactics: 'सर्व घटना',
  sources: { rules: 'नियम', model: 'मॉडेल', alert: 'अलर्ट', connection: 'कनेक्शन', voice: 'आवाजाची तपासणी', system: 'सिस्टम' },
  eventsTitle: 'काय झाले, पायरी पायरीने', callTime: 'कॉलची वेळ', clockTime: 'घड्याळाची वेळ', noEvents: 'कोणतीही घटना जुळली नाही.',
  transcriptTitle: 'काय बोलले गेले', track: 'ट्रान्सक्रिप्ट', noTranscript: 'कोणतेही शब्द ट्रान्सक्राइब झाले नाहीत.',
  timesNote: 'वेळ म्हणजे अ‍ॅपला शब्द मिळाले तेव्हाची. स्पीच-टू-टेक्स्ट सेवा ते बोलल्यानंतर एक-दोन सेकंदांनी देऊ शकते.',
  maskedNote: 'या अहवालात बोललेले अंक लपवले आहेत (• ने दाखवले).',
  ev: {
    callStarted: 'तपासणी सुरू झाली', firstWords: 'पहिले शब्द ऐकले गेले', joined: 'फोन कॉलशी जोडला गेला', dropped: 'फोनचे कनेक्शन तुटले',
    rejoined: 'फोन पुन्हा जोडला गेला', listenOn: 'ऐकणे सुरू केले', listenOff: 'ऐकणे बंद केले', ended: 'कॉल संपला',
    warning: 'स्पीच-टू-टेक्स्ट सेवेने अडचण कळवली', voice: 'आवाजाची तपासणी पूर्ण झाली',
    level: (f, to, by) => `धोका ${f} वरून ${to} झाला (${by})`, model: (p) => `भाषा मॉडेलने कॉलला ${p}% फसवणुकीसारखा ठरवले`, alert: (l) => `अलर्ट दाखवला: ${l}`,
  },
  ai: {
    title: 'AI ने लिहिलेला सारांश', notSet: 'अजून कोणतीही AI सेवा सुरू नाही, म्हणून फक्त थोडक्यात सारांश दिसतो.',
    howTo: 'ती सुरू करण्यासाठी .env फाइलमध्ये किल्ल्या जोडा (.env.example पहा) आणि सर्व्हर पुन्हा सुरू करा.',
    consent: (to) => `हा सारांश लिहिण्यासाठी कॉलचा मजकूर (अंक लपवलेले, ऑडिओ नाही) ${to} कडे पाठवा`, auto: 'प्रत्येक कॉलसाठी आपोआप लिहा',
    write: 'AI सारांश लिहा', writing: 'सारांश लिहिला जात आहे…', again: 'पुन्हा लिहा', by: (m) => `ओपन मॉडेल ${m} ने लिहिले`, fellBack: (n) => `आधी ${n} इतर मोफत मॉडेल उपलब्ध किंवा उपयोगी नव्हती.`,
    warn: 'AI ने लिहिलेल्या मजकुरात चुका असू शकतात. निकाल, कालरेषा आणि ठळक शब्द नियमांवरून येतात, AI वरून नाही.',
    happened: 'काय झाले', why: 'हे धोकादायक का वाटले', advice: 'काय करावे', quotes: 'उद्धृत शब्द', langNote: 'सारांशाची भाषा',
  },
  loading: 'अहवाल लोड होत आहे…', loadError: 'अहवाल लोड करता आला नाही.', noTimeline: 'या विश्लेषणाची कालरेषा नाही. फक्त लाइव्ह कॉलची कालरेषा तयार होते.',
}

export const RTEXT: Record<Lang, ReportText> = { en, hi, mr }
