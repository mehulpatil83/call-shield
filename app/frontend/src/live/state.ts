import type { Hit, Level } from '../types'

export interface LiveTrack { code: string; text: string; hits: Hit[] }
export interface LiveState {
  status: 'idle' | 'connecting' | 'live' | 'stopping' | 'ended' | 'error'
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
    case 'analysis':
      return { ...state, level: msg.level, score: msg.score, summary: msg.summary, seconds: msg.seconds, tracks: msg.tracks, hits: msg.hits }
    case 'alert': return { ...state, alert: state.alert && RANK[state.alert] >= RANK[msg.level] ? state.alert : msg.level }
    case 'ended': return { ...state, status: 'ended', id: msg.id, message: msg.message ?? null }
    case 'error': return { ...state, status: 'error', message: msg.message }
    case 'warning': return { ...state, warning: msg.message }
    case 'limit': return { ...state, warning: `limit:${msg.seconds}` }
  }
}
