/** Sound and speech for the alert, kept in one object so tests can replace them. No audio files: the tone is generated. */
export type AlertLevel = 'elevated' | 'high'
export type SpeakResult = 'spoken' | 'unavailable'

interface VoiceLike { lang: string }
interface SynthLike { getVoices: () => VoiceLike[]; speak: (u: SpeechSynthesisUtterance) => void; cancel: () => void }

const WANT: Record<'en' | 'hi' | 'mr', string> = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' }

/** Pick a voice for the language. Returns undefined when none fits (or when the voice list is not loaded yet). */
export function pickVoice<T extends VoiceLike>(voices: T[], lang: 'en' | 'hi' | 'mr'): T | undefined {
  const norm = (v: VoiceLike) => v.lang.replace('_', '-').toLowerCase()
  const want = WANT[lang].toLowerCase()
  return voices.find((v) => norm(v) === want)
    ?? voices.find((v) => norm(v).startsWith(lang))
    ?? (lang === 'mr' ? voices.find((v) => norm(v).startsWith('hi')) : undefined)      // Marathi shares the Devanagari script with Hindi
    ?? (lang === 'en' ? voices.find((v) => norm(v).startsWith('en')) : undefined)
}

export function speakText(text: string, lang: 'en' | 'hi' | 'mr', synth: SynthLike | undefined = window.speechSynthesis as SynthLike | undefined): SpeakResult {
  if (!synth) return 'unavailable'
  const voices = synth.getVoices()
  const voice = pickVoice(voices, lang)
  if (voices.length > 0 && !voice && lang !== 'en') return 'unavailable'               // never read Devanagari with an English voice
  const u = new SpeechSynthesisUtterance(text)
  u.lang = voice?.lang ?? WANT[lang]
  if (voice) u.voice = voice as unknown as SpeechSynthesisVoice
  u.rate = 0.95
  synth.cancel()
  synth.speak(u)
  return 'spoken'
}

export function stopSpeaking(synth: SynthLike | undefined = window.speechSynthesis as SynthLike | undefined): void {
  try { synth?.cancel() } catch { /* nothing to stop */ }
}

/** A short generated siren (high) or single soft beep (elevated). Needs the page to have had a click, which starting a call is. */
export function playTone(level: AlertLevel): void {
  const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctx) return
  try {
    const ctx = new Ctx()
    const gain = ctx.createGain()
    gain.gain.value = level === 'high' ? 0.22 : 0.12
    gain.connect(ctx.destination)
    const beats = level === 'high' ? [880, 660, 880, 660] : [660]
    const len = level === 'high' ? 0.25 : 0.2
    beats.forEach((hz, i) => {
      const o = ctx.createOscillator()
      o.type = 'sine'
      o.frequency.value = hz
      o.connect(gain)
      o.start(ctx.currentTime + i * len)
      o.stop(ctx.currentTime + (i + 1) * len - 0.02)
    })
    window.setTimeout(() => { void ctx.close() }, (beats.length * len + 0.3) * 1000)
  } catch { /* sound is a bonus: the screen alert still shows */ }
}

export const alertDeps = { playTone, speakText, stopSpeaking }
