import type { SessionResponse, AiResult } from './report/types'
import type { AnalysisDetail, AnalysisSummary, Health, Lang, SpeechLang } from './types'

export class ApiError extends Error {}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new ApiError('Cannot reach the call-shield server. Is it still running?')
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep the generic message */ }
    throw new ApiError(detail)
  }
  return res.json() as Promise<T>
}

export const health = () => call<Health>('/api/health')
export const listAnalyses = () => call<AnalysisSummary[]>('/api/analyses')
export const getAnalysis = (id: string) => call<AnalysisDetail>(`/api/analyses/${id}`)
export const deleteAnalysis = (id: string) => call<{ deleted: string }>(`/api/analyses/${id}`, { method: 'DELETE' })
export const deleteAll = () => call<{ deleted: number }>('/api/analyses', { method: 'DELETE' })
export const reportHtmlUrl = (id: string) => `/api/analyses/${id}/report.html?download=true`

export function createAnalysis(file: File, language: SpeechLang, consent: boolean, skipAudioCheck: boolean, conversation = false) {
  const form = new FormData()
  form.append('file', file)
  form.append('language', language)
  form.append('consent', String(consent))
  form.append('skip_audio_check', String(skipAudioCheck))
  form.append('conversation', String(conversation))
  return call<{ id: string; status: string }>('/api/analyses', { method: 'POST', body: form })
}

export interface CallCreated { code: string; language: string; public_url: string | null; join_url: string | null; expires_in: number }
export const callConfig = () => call<{ public_url: string | null }>('/api/calls/config')
export function createCall(language: SpeechLang, consent: boolean, skipAudioCheck: boolean, publicUrl: string | null) {
  return call<CallCreated>('/api/calls', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language, consent, skip_audio_check: skipAudioCheck, public_url: publicUrl || null }),
  })
}

export const getSession = (id: string) => call<SessionResponse>(`/api/analyses/${id}/session`)
export function writeAi(id: string, lang: Lang, consent: boolean, force = false) {
  return call<{ ai: AiResult; cached: boolean }>(`/api/analyses/${id}/ai`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lang, consent, force }),
  })
}
