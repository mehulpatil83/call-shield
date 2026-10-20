import type { Level, SpeechLang } from '../types'
import type { LiveEvent, LiveState } from '../live/state'

/** Every scam tactic the rules can report (cautions are not tactics). Same ids as core/lexicon.py and core/rules.py. */
export const TACTICS: { id: string; kind: 'request' | 'pressure' | 'context' }[] = [
  { id: 'otp_request', kind: 'request' }, { id: 'credential_request', kind: 'request' },
  { id: 'payment_request', kind: 'request' }, { id: 'remote_access', kind: 'request' },
  { id: 'urgency', kind: 'pressure' }, { id: 'threat', kind: 'pressure' },
  { id: 'secrecy', kind: 'pressure' }, { id: 'verification_bypass', kind: 'pressure' },
  { id: 'authority', kind: 'context' }, { id: 'kyc_pretext', kind: 'context' }, { id: 'account_alert', kind: 'context' },
]

export const RUPEES_PER_MIN = 0.47                       // measured for one Gnani stream in phase 0 (core/config.py)
export const STREAMS: Record<SpeechLang, number> = { en: 1, hi: 1, mr: 1, hinglish: 2, auto: 3 }

export const estimateRupees = (seconds: number, language: SpeechLang): number => (Math.max(0, seconds) / 60) * RUPEES_PER_MIN * STREAMS[language]

export function formatClock(sec: number): string {
  const s = Math.max(0, Math.floor(sec))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export const heardCategories = (events: LiveEvent[]): Set<string> => new Set(events.filter((e) => e.kind === 'tactic').map((e) => e.category!))

/** What the caller is asking for, most recent first. */
export function wantsNow(events: LiveEvent[]): string[] {
  return events.filter((e) => e.kind === 'tactic' && e.hitKind === 'request').map((e) => e.category!).reverse()
}

export interface Scorecard {
  verdict: Level
  duration: number
  peakScore: number
  firstWarningAt: number | null
  highAlertAt: number | null
  firstRequestAt: number | null
  tactics: string[]
}

/** Facts for the end-of-call card. Times are audio seconds as seen on this screen. */
export function scorecard(s: Pick<LiveState, 'events' | 'history' | 'seconds' | 'level' | 'finalLevel'>): Scorecard {
  const alerts = s.events.filter((e) => e.kind === 'alert')
  const reqs = s.events.filter((e) => e.kind === 'tactic' && e.hitKind === 'request')
  return {
    verdict: s.finalLevel ?? s.level,
    duration: s.seconds,
    peakScore: s.history.reduce((m, p) => Math.max(m, p.score), 0),
    firstWarningAt: alerts.length ? Math.min(...alerts.map((e) => e.t)) : null,
    highAlertAt: alerts.find((e) => e.alertLevel === 'high')?.t ?? null,
    firstRequestAt: reqs.length ? Math.min(...reqs.map((e) => e.t)) : null,
    tactics: [...heardCategories(s.events)],
  }
}
