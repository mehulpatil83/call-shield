import type { Level } from '../types'

export type Source = 'rules' | 'model' | 'alert' | 'connection' | 'voice' | 'system'
export const SOURCES: Source[] = ['rules', 'model', 'alert', 'connection', 'voice', 'system']

/** One thing that happened in the call. `t` = seconds of audio received so far, `wall` = the laptop clock at that moment. */
export interface SessionEvent {
  i: number; t: number; wall: string; source: Source; kind: string
  category?: string; kind_of?: string; quote?: string; track?: string; explanation?: string   // tactic
  frm?: Level; to?: Level; score?: number                                                      // level
  prob?: number; threshold?: number; would_raise?: Level                                       // model
  level?: Level; message?: string; on?: boolean; reason?: string; label?: string; status?: string
}
export interface SessionSegment { track: string; first_t: number; last_t: number; first_wall: string; text: string }
export interface RiskPoint { t: number; level: Level; score: number; model: number | null }
export interface Session {
  version: number; id?: string; started_at: string; language: string; call_language?: string; duration: number
  max_level: Level; level: Level; digits_masked: boolean; timestamps_note: string
  segments: SessionSegment[]; events: SessionEvent[]; risk: RiskPoint[]
}
export interface AiResult {
  lang: string; model: string; provider: string; made_at: string; summary: string
  what_happened: { at: number | null; text: string }[]; why_risky: string[]; advice: string[]; quotes: string[]; dropped_quotes: number
  /** the models that were tried, in order (the last one wrote the summary) */
  attempts?: { model: string; result: string }[]
}
export interface AiStatus { configured: boolean; provider: string | null; model: string | null; sends_to: string | null }
export interface SessionResponse { session: Session; ai: Record<string, AiResult>; ai_status: AiStatus }
