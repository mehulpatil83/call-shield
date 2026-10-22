import type { Hit, Level } from '../types'

/** The language model's second opinion, as reported by the server with every analysis. */
export interface ModelInfo { status: 'off' | 'loading' | 'ready' | 'unavailable'; prob: number | null; peak: number; raised: boolean }
export interface LiveTrack { code: string; text: string; hits: Hit[] }
/** One step of the risk graph: when (audio seconds), how high, and which tactics were heard for the first time here. */
export interface LivePoint { t: number; score: number; level: Level; fresh: { category: string; quote: string }[] }
/** Something worth a line on the timeline: a tactic heard for the first time, or an alert that was shown. */
export interface LiveEvent { id: string; t: number; kind: 'tactic' | 'alert'; category?: string; hitKind?: Hit['kind']; quote?: string; alertLevel?: Level }
export interface LiveState {
  status: 'idle' | 'connecting' | 'waiting' | 'joined' | 'live' | 'reconnecting' | 'stopping' | 'ended' | 'error'
  level: Level
  score: number
  summary: string
  seconds: number
  tracks: LiveTrack[]
  hits: Hit[]
  alert: Level | null
  id: string | null
  message: string | null
  warning: string | null
  history: LivePoint[]
  events: LiveEvent[]
  /** the highest risk level of the whole call, known once it has ended */
  finalLevel: Level | null
  /** the model's second opinion (absent until the first analysis, or from an older server) */
  model?: ModelInfo | null
}

export const initialLive: LiveState = {
  status: 'idle', level: 'low', score: 0, summary: '', seconds: 0, tracks: [], hits: [], alert: null, id: null, message: null, warning: null, history: [], events: [], finalLevel: null,
}

const RANK: Record<Level, number> = { low: 0, elevated: 1, high: 2 }

export type ServerMessage =
  | { type: 'ready' }
  | { type: 'call'; state: 'waiting' | 'joined' | 'reconnecting' | 'live'; seconds?: number }
  | { type: 'analysis'; level: Level; score: number; summary: string; seconds: number; tracks: LiveTrack[]; hits: Hit[]; model?: ModelInfo }
  | { type: 'alert'; level: Level }
  | { type: 'ended'; id: string | null; message?: string; level?: Level; max_level?: Level }
  | { type: 'error'; message: string }
  | { type: 'warning'; message: string }
  | { type: 'limit'; seconds: number }

/** Pure reducer: easy to test without a browser, microphone or server. */
export function liveReducer(state: LiveState, msg: ServerMessage): LiveState {
  switch (msg.type) {
    case 'ready': return { ...state, status: 'live' }
    case 'call':
      if (msg.state === 'reconnecting') return state.status === 'live' ? { ...state, status: 'reconnecting' } : state
      if (msg.state === 'live') return state.status === 'reconnecting' ? { ...state, status: 'live' } : state
      if (['live', 'reconnecting', 'stopping', 'ended'].includes(state.status)) return state
      return { ...state, status: msg.state }
    case 'analysis': {
      const seen = new Set(state.events.filter((e) => e.kind === 'tactic').map((e) => e.category))
      const fresh: LiveEvent[] = []
      for (const h of msg.hits) {
        if (h.kind === 'warning' || seen.has(h.category)) continue          // a caution is not a scam tactic; each tactic is listed once
        seen.add(h.category)
        fresh.push({ id: `tactic-${h.category}`, kind: 'tactic', t: msg.seconds, category: h.category, hitKind: h.kind, quote: h.quote })
      }
      const point: LivePoint = { t: msg.seconds, score: msg.score, level: msg.level, fresh: fresh.map((e) => ({ category: e.category!, quote: e.quote! })) }
      return {
        ...state, level: msg.level, score: msg.score, summary: msg.summary, seconds: msg.seconds, tracks: msg.tracks, hits: msg.hits, model: msg.model ?? state.model ?? null,
        history: [...state.history, point].slice(-600), events: fresh.length ? [...state.events, ...fresh] : state.events,
      }
    }
    case 'alert': {
      const has = state.events.some((e) => e.kind === 'alert' && e.alertLevel === msg.level)
      return {
        ...state,
        alert: state.alert && RANK[state.alert] >= RANK[msg.level] ? state.alert : msg.level,
        events: has ? state.events : [...state.events, { id: `alert-${msg.level}`, kind: 'alert', t: state.seconds, alertLevel: msg.level }],
      }
    }
    case 'ended': return { ...state, status: 'ended', id: msg.id, message: msg.message ?? null, finalLevel: msg.max_level ?? state.level }
    case 'error': return { ...state, status: 'error', message: msg.message }
    case 'warning': return { ...state, warning: msg.message }
    case 'limit': return { ...state, warning: `limit:${msg.seconds}` }
    default: return state                       // a message type this page does not know must never break it
  }
}

export type LiveAction = ServerMessage | { type: '_reset' } | { type: '_connecting' } | { type: '_stopping' }

/** Reducer for a whole live session: server messages plus the page's own start / stop / reset actions. */
export function reduceLive(state: LiveState, a: LiveAction): LiveState {
  if (a.type === '_reset') return initialLive
  if (a.type === '_connecting') return { ...initialLive, status: 'connecting' }
  if (a.type === '_stopping') return ['live', 'reconnecting', 'joined', 'waiting'].includes(state.status) ? { ...state, status: 'stopping' } : state
  return liveReducer(state, a)
}
