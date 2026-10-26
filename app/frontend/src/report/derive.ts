import { categoryText, type Dict } from '../i18n'
import type { Level } from '../types'
import type { ReportText } from './strings'
import type { Session, SessionEvent, SessionSegment, Source } from './types'

export function fmtCall(t: number): string {
  const s = Math.max(0, t)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${(s % 60).toFixed(1).padStart(4, '0')}`
}

export function fmtClock(iso: string): string {
  const m = /T(\d{2}:\d{2}:\d{2})/.exec(iso)
  return m ? m[1] : iso
}

export interface Stats {
  duration: number; level: Level; maxLevel: Level; firstAlertAt: number | null; highAt: number | null
  tactics: string[]; modelPeak: number | null; voice: string | null
}

export function stats(s: Session): Stats {
  const alerts = s.events.filter((e) => e.kind === 'alert')
  const probs = [...s.events.filter((e) => e.kind === 'model').map((e) => e.prob ?? 0), ...s.risk.map((r) => r.model ?? 0)]
  const tactics: string[] = []
  for (const e of s.events) if (e.kind === 'tactic' && e.kind_of !== 'warning' && e.category && !tactics.includes(e.category)) tactics.push(e.category)
  return {
    duration: s.duration, level: s.level, maxLevel: s.max_level,
    firstAlertAt: alerts.length ? alerts[0].t : null, highAt: alerts.find((e) => e.level === 'high')?.t ?? null,
    tactics, modelPeak: probs.length && Math.max(...probs) > 0 ? Math.max(...probs) : null,
    voice: s.events.find((e) => e.kind === 'voice_check')?.label ?? null,
  }
}

/** One readable line for an event (and the exact quoted words, when there are any). */
export function describe(ev: SessionEvent, r: ReportText, t: Dict): { text: string; quote?: string } {
  const lv = (l?: Level) => (l ? r.levelShort[l] : '')
  switch (ev.kind) {
    case 'call_started': return { text: r.ev.callStarted }
    case 'first_words': return { text: r.ev.firstWords }
    case 'tactic': return { text: categoryText(t, ev.category ?? '').label, quote: ev.quote }
    case 'level': return { text: r.ev.level(lv(ev.frm), lv(ev.to), r.sources[ev.source]) }
    case 'model': return { text: r.ev.model(Math.round((ev.prob ?? 0) * 100)) }
    case 'alert': return { text: r.ev.alert(lv(ev.level)) }
    case 'warning': return { text: r.ev.warning, quote: ev.message }
    case 'phone_joined': return { text: r.ev.joined }
    case 'phone_dropped': return { text: r.ev.dropped }
    case 'phone_rejoined': return { text: r.ev.rejoined }
    case 'listen': return { text: ev.on ? r.ev.listenOn : r.ev.listenOff }
    case 'ended': return { text: r.ev.ended }
    case 'voice_check': return { text: r.ev.voice, quote: ev.label }
    default: return { text: ev.kind.replace(/_/g, ' ') }
  }
}

export interface Filters { sources: Set<Source>; category: string | null; query: string }

export function filterEvents(events: SessionEvent[], f: Filters, r: ReportText, t: Dict): SessionEvent[] {
  const q = f.query.trim().toLowerCase()
  return events.filter((e) => {
    if (!f.sources.has(e.source)) return false
    if (f.category && !(e.kind === 'tactic' && e.category === f.category)) return false
    if (!q) return true
    const d = describe(e, r, t)
    return `${d.text} ${d.quote ?? ''}`.toLowerCase().includes(q)
  })
}

/** Index of the last event at or before the cursor, or -1. */
export function currentIndex(events: SessionEvent[], cursor: number | null): number {
  if (cursor === null) return -1
  let idx = -1
  events.forEach((e, i) => { if (e.t <= cursor) idx = i })
  return idx
}

export function primaryTrack(segments: SessionSegment[]): string | null {
  const len: Record<string, number> = {}
  for (const s of segments) len[s.track] = (len[s.track] ?? 0) + s.text.length
  const tracks = Object.keys(len)
  if (!tracks.length) return null
  return tracks.includes('en-IN') ? 'en-IN' : tracks.sort((a, b) => len[b] - len[a])[0]
}

/** Split text so the quoted evidence can be marked. Matching ignores case; overlapping quotes are skipped. */
export function markQuotes(text: string, quotes: string[]): { text: string; hit: boolean }[] {
  const low = text.toLowerCase()
  const spans: [number, number][] = []
  for (const q of quotes.filter(Boolean)) {
    let from = 0
    const ql = q.toLowerCase()
    for (;;) {
      const i = low.indexOf(ql, from)
      if (i < 0) break
      spans.push([i, i + ql.length])
      from = i + ql.length
    }
  }
  spans.sort((a, b) => a[0] - b[0] || b[1] - a[1])
  const out: { text: string; hit: boolean }[] = []
  let pos = 0
  for (const [s, e] of spans) {
    if (s < pos) continue
    if (s > pos) out.push({ text: text.slice(pos, s), hit: false })
    out.push({ text: text.slice(s, e), hit: true })
    pos = e
  }
  if (pos < text.length) out.push({ text: text.slice(pos), hit: false })
  return out.length ? out : [{ text, hit: false }]
}

const RANK: Record<Level, number> = { low: 0, elevated: 1, high: 2 }

/** The highest level the RULES alone reached (what they found, without the language model). */
export function rulesLevel(s: Session): Level {
  let best: Level = 'low'
  for (const e of s.events) if (e.kind === 'level' && e.source === 'rules' && e.to && RANK[e.to] > RANK[best]) best = e.to
  return best
}

/** Who pushed the call to its final level: the rules, or the language model (and when). */
export function decidedBy(s: Session): { by: 'rules' | 'model' | 'none'; at: number | null } {
  if (s.max_level === 'low') return { by: 'none', at: null }
  const e = s.events.find((x) => x.kind === 'level' && x.to === s.max_level)
  if (!e) return { by: 'rules', at: null }
  return { by: e.source === 'model' ? 'model' : 'rules', at: e.t }
}

export function modelRaisedAt(s: Session): number | null {
  return s.events.find((x) => x.kind === 'level' && x.source === 'model')?.t ?? null
}

export function firstSentence(text: string): string {
  return text.match(/^.*?[.!?।](\s|$)/s)?.[0].trim() ?? text
}
