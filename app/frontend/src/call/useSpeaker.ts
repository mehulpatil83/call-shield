import { useCallback, useEffect, useRef, useState } from 'react'
import { startMicrophone } from '../live/audio'
import { rmsOfPcm16 } from '../live/pcm'

export type SpeakerStatus = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'ended' | 'error'
export interface SpeakerState {
  status: SpeakerStatus
  error: 'mic' | 'connection' | 'server' | null
  message: string | null
  seconds: number
  muted: boolean
  /** microphone loudness for the on-screen bar, 0..1 */
  level: number
  /** true when nothing has been heard for a while although the call is live and not muted */
  silent: boolean
  /** a call that was running when this page was reloaded or discarded and can still be rejoined */
  resumable: { code: string } | null
}

export const GRACE_MS = 60_000      // how long the server keeps a dropped call open
export const RETRY_MS = 1_500
export const SILENCE_MS = 8_000
export const VOICE_RMS = 0.01
const STORE_KEY = 'cs-call'

const INITIAL: SpeakerState = { status: 'idle', error: null, message: null, seconds: 0, muted: false, level: 0, silent: false, resumable: null }

export function speakUrl(code: string, resume?: string | null): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/call/speak?code=${code}${resume ? `&resume=${encodeURIComponent(resume)}` : ''}`
}

interface Saved { code: string; token: string; at: number }
function loadSaved(): Saved | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(STORE_KEY) ?? 'null') as Saved | null
    return v && Date.now() - v.at < GRACE_MS ? v : null
  } catch { return null }
}
function save(v: Saved | null): void {
  try { if (v) sessionStorage.setItem(STORE_KEY, JSON.stringify(v)); else sessionStorage.removeItem(STORE_KEY) } catch { /* private mode: rejoin after a reload just will not be offered */ }
}

export interface SpeakerDeps {
  createSocket?: (url: string) => WebSocket
  mic?: (onChunk: (pcm: ArrayBuffer) => void) => Promise<() => void>
}

/** The Speaker side (the phone): consent message, microphone -> server, level bar, silence warning, mute, timer, screen wake
 *  lock, and automatic rejoin of the same call after a dropped connection or a screen lock. Shows no analysis. */
export function useSpeaker(deps: SpeakerDeps = {}) {
  const createSocket = deps.createSocket ?? ((u: string) => new WebSocket(u))
  const mic = deps.mic ?? startMicrophone
  const [state, setState] = useState<SpeakerState>(() => ({ ...INITIAL, resumable: loadSaved() ? { code: loadSaved()!.code } : null }))
  const socket = useRef<WebSocket | null>(null)
  const stopMic = useRef<(() => void) | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const retry = useRef<number | undefined>(undefined)
  const lock = useRef<{ release: () => Promise<void> } | null>(null)
  const muted = useRef(false)
  const finished = useRef(false)
  const code = useRef('')
  const token = useRef<string | null>(null)
  const droppedAt = useRef(0)
  const lastVoice = useRef(0)
  const lastLevelUpdate = useRef(0)
  const began = useRef(0)
  const openRef = useRef<(c: string, resume?: string | null) => void>(() => undefined)

  const stopAudio = useCallback(() => {
    stopMic.current?.()
    stopMic.current = null
    void lock.current?.release().catch(() => undefined)
    lock.current = null
  }, [])
  const cleanup = useCallback(() => {
    stopAudio()
    window.clearInterval(timer.current)
    window.clearTimeout(retry.current)
  }, [stopAudio])
  useEffect(() => () => { cleanup(); socket.current?.close() }, [cleanup])

  const fail = useCallback((error: SpeakerState['error'], message: string | null = null) => {
    finished.current = true
    cleanup()
    save(null)
    setState((s) => ({ ...s, status: 'error', error, message, level: 0, silent: false }))
  }, [cleanup])

  const startAudio = useCallback(async (): Promise<boolean> => {
    stopAudio()
    try {
      const wl = (navigator as unknown as { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }).wakeLock
      try { lock.current = (await wl?.request('screen')) ?? null } catch { /* screen lock is a bonus, not a requirement */ }
      stopMic.current = await mic((chunk) => {
        const rms = rmsOfPcm16(chunk)
        const now = Date.now()
        if (!muted.current && rms > VOICE_RMS) lastVoice.current = now
        if (now - lastLevelUpdate.current >= 100) {
          lastLevelUpdate.current = now
          const level = muted.current ? 0 : Math.min(1, rms * 5)
          setState((s) => (Math.abs(s.level - level) > 0.02 ? { ...s, level } : s))
        }
        const ws = socket.current
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(muted.current ? new ArrayBuffer(chunk.byteLength) : chunk)   // muted: send silence so timing stays right
      })
      return true
    } catch {
      return false
    }
  }, [mic, stopAudio])

  const beginTimers = useCallback(() => {
    window.clearInterval(timer.current)
    timer.current = window.setInterval(() => {
      const now = Date.now()
      if (token.current && code.current) save({ code: code.current, token: token.current, at: now })
      setState((s) => ({
        ...s,
        seconds: Math.floor((now - began.current) / 1000),
        silent: s.status === 'live' && !muted.current && now - lastVoice.current > SILENCE_MS,
      }))
    }, 1000)
  }, [])

  const scheduleRetry = useCallback((immediately = false) => {
    window.clearTimeout(retry.current)
    if (Date.now() - droppedAt.current > GRACE_MS) { fail('connection'); return }
    retry.current = window.setTimeout(() => openRef.current(code.current, token.current), immediately ? 0 : RETRY_MS)
  }, [fail])

  const open = useCallback((c: string, resume: string | null = null) => {
    finished.current = false
    code.current = c
    const ws = createSocket(speakUrl(c, resume))
    ws.binaryType = 'arraybuffer'
    socket.current = ws
    ws.onmessage = async (ev) => {
      if (socket.current !== ws) return
      const msg = JSON.parse(ev.data as string) as { type: string; message?: string; resume?: string; resumed?: boolean }
      if (msg.type === 'joined') {
        ws.send(JSON.stringify({ type: 'hello', consent: true }))
      } else if (msg.type === 'ready') {
        token.current = msg.resume ?? token.current
        if (token.current) save({ code: c, token: token.current, at: Date.now() })
        if (!(await startAudio())) { ws.close(); fail('mic'); return }
        lastVoice.current = Date.now()
        droppedAt.current = 0
        if (began.current === 0) began.current = Date.now()
        beginTimers()
        setState((s) => ({ ...s, status: 'live', error: null, message: null, silent: false, resumable: null }))
      } else if (msg.type === 'ended') {
        finished.current = true
        cleanup()
        save(null)
        setState((s) => (s.status === 'error' ? s : { ...s, status: 'ended', level: 0, silent: false }))
      } else if (msg.type === 'error') {
        fail('server', msg.message ?? null)
      }
    }
    const dropped = () => {
      if (finished.current || socket.current !== ws) return
      if (!token.current) { fail('connection'); return }          // not started yet: nothing to rejoin
      if (droppedAt.current === 0) droppedAt.current = Date.now()
      stopAudio()
      setState((s) => (s.status === 'live' || s.status === 'reconnecting' || s.status === 'connecting' ? { ...s, status: 'reconnecting', level: 0, silent: false } : s))
      scheduleRetry()
    }
    ws.onerror = dropped
    ws.onclose = dropped
  }, [beginTimers, cleanup, createSocket, fail, scheduleRetry, startAudio, stopAudio])
  openRef.current = open

  const join = useCallback((c: string) => {
    muted.current = false
    token.current = null
    droppedAt.current = 0
    began.current = 0
    save(null)
    setState({ ...INITIAL, status: 'connecting' })
    open(c)
  }, [open])

  /** After a page reload: take the saved call back (needs a tap, so the browser allows the microphone and sound). */
  const rejoin = useCallback(() => {
    const saved = loadSaved()
    if (!saved) { setState((s) => ({ ...s, resumable: null })); return }
    muted.current = false
    token.current = saved.token
    droppedAt.current = Date.now()
    began.current = 0
    setState({ ...INITIAL, status: 'reconnecting' })
    open(saved.code, saved.token)
  }, [open])

  // coming back to the page (screen unlocked): do not wait for the next retry tick
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible' && !finished.current && token.current && socket.current?.readyState !== WebSocket.OPEN) {
        if (droppedAt.current === 0) droppedAt.current = Date.now()
        scheduleRetry(true)
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [scheduleRetry])

  const toggleMute = useCallback(() => {
    muted.current = !muted.current
    setState((s) => ({ ...s, muted: muted.current, level: muted.current ? 0 : s.level, silent: false }))
    if (!muted.current) lastVoice.current = Date.now()
  }, [])

  const leave = useCallback(() => {
    const ws = socket.current
    finished.current = true
    cleanup()
    save(null)
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
    else setState((s) => ({ ...s, status: 'ended', level: 0, silent: false }))
  }, [cleanup])

  const reset = useCallback(() => {
    finished.current = true
    cleanup()
    save(null)
    socket.current?.close()
    setState(INITIAL)
  }, [cleanup])

  const forget = useCallback(() => { save(null); setState((s) => ({ ...s, resumable: null })) }, [])

  return { state, join, rejoin, forget, toggleMute, leave, reset }
}
