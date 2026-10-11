export type Lang = 'en' | 'hi' | 'mr'
export type SpeechLang = 'en' | 'hinglish' | 'mr' | 'hi'
export type Level = 'high' | 'elevated' | 'low'
export type Status = 'queued' | 'running' | 'done' | 'error'
export type Step = 'transcribing' | 'analysing' | 'checking_audio'

export interface Hit {
  category: string
  kind: 'request' | 'pressure' | 'context' | 'warning'
  quote: string
  start: number
  end: number
  explanation: string
  source: string
}
export interface DigitRun { digits: string; start: number; end: number; quote: string }
export interface TranscriptEntry {
  code: string
  mode: string
  text: string
  rules: { hits: Hit[] }
}
export interface Authenticity {
  status: 'ok' | 'inconclusive' | 'unavailable'
  label: string
  code: 'natural' | 'synthetic' | 'inconclusive_band' | 'inconclusive_short' | 'unavailable' | ''
  reason: string
  median: number | null
  q25: number | null
  q75: number | null
  n_windows: number
  window_scores: number[]
  real_at_least: number
  synth_at_most: number
  note: string
  plain_note: string
  model: string
}
export interface Report {
  meta: { file: string; language: string; created: string; audio_seconds: number | null; est_cost_rupees: number; stt_models: string[] }
  plain_summary: string
  advice: string[]
  transcripts: TranscriptEntry[]
  conversation: {
    level: Level
    label: string
    score: number
    summary: string
    hits: Hit[]
    digit_runs: DigitRun[]
    digit_note: string
  }
  authenticity: Authenticity | null
  limitations: string[]
}
export interface AnalysisSummary {
  id: string
  filename: string
  created: string
  language: string
  status: Status
  step: Step | null
  error: string | null
  level: Level | null
  auth_label: string | null
  est_rupees: number | null
}
export interface AnalysisDetail extends AnalysisSummary { report: Report | null }
export interface Health {
  ok: boolean
  version: string
  gnani_key_present: boolean
  languages: Record<string, string>
  max_upload_mb: number
}
