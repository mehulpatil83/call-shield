import type { Hit, Level } from '../types'

export interface LiveTrack { code: string; text: string; hits: Hit[] }
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
}

export const initialLive: LiveState = {
  status: 'idle', level: 'low', score: 0, summary: '', seconds: 0, tracks: [], hits: [], alert: null, id: null, message: null, warning: null,
}

const RANK: Record<Level, number> = { low: 0, elevated: 1, high: 2 }

export type ServerMessage =
  | { type: 'ready' }
  | { type: 'call'; state: 'waiting' | 'joined' | 'reconnecting' | 'live'; seconds?: number }
  | { type: 'analysis'; level: Level; score: number; summary: string; seconds: number; tracks: LiveTrack[]; hits: Hit[] }
  | { type: 'alert'; level: Level }
  | { type: 'ended'; id: string | null; message?: string }
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
    case 'analysis':
      return { ...state, level: msg.level, score: msg.score, summary: msg.summary, seconds: msg.seconds, tracks: msg.tracks, hits: msg.hits }
    case 'alert': return { ...state, alert: state.alert && RANK[state.alert] >= RANK[msg.level] ? state.alert : msg.level }
    case 'ended': return { ...state, status: 'ended', id: msg.id, message: msg.message ?? null }
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
