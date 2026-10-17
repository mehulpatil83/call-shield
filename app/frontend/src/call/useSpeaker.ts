import { useCallback, useEffect, useRef, useState } from 'react'
import { startMicrophone } from '../live/audio'

export type SpeakerStatus = 'idle' | 'connecting' | 'live' | 'ended' | 'error'
export interface SpeakerState {
  status: SpeakerStatus
  error: 'mic' | 'connection' | 'server' | null
  message: string | null
  seconds: number
  muted: boolean
}
const INITIAL: SpeakerState = { status: 'idle', error: null, message: null, seconds: 0, muted: false }

export function speakUrl(code: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/call/speak?code=${code}`
}

export interface SpeakerDeps {
  createSocket?: (url: string) => WebSocket
  mic?: (onChunk: (pcm: ArrayBuffer) => void) => Promise<() => void>
}

/** The Speaker side (the phone): consent message, microphone -> server, mute, timer, screen wake lock. Shows no analysis. */
export function useSpeaker(deps: SpeakerDeps = {}) {
  const createSocket = deps.createSocket ?? ((u: string) => new WebSocket(u))
  const mic = deps.mic ?? startMicrophone
  const [state, setState] = useState<SpeakerState>(INITIAL)
  const socket = useRef<WebSocket | null>(null)
  const stopMic = useRef<(() => void) | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const lock = useRef<{ release: () => Promise<void> } | null>(null)
  const muted = useRef(false)
  const finished = useRef(false)

  const cleanup = useCallback(() => {
    stopMic.current?.()
    stopMic.current = null
    window.clearInterval(timer.current)
    void lock.current?.release().catch(() => undefined)
    lock.current = null
  }, [])
  useEffect(() => () => { cleanup(); socket.current?.close() }, [cleanup])

  const fail = useCallback((error: SpeakerState['error'], message: string | null = null) => {
    finished.current = true
    cleanup()
    setState((s) => ({ ...s, status: 'error', error, message }))
  }, [cleanup])

  const join = useCallback((code: string) => {
    finished.current = false
    muted.current = false
    setState({ ...INITIAL, status: 'connecting' })
    const ws = createSocket(speakUrl(code))
    ws.binaryType = 'arraybuffer'
    socket.current = ws
    ws.onmessage = async (ev) => {
      const msg = JSON.parse(ev.data as string) as { type: string; message?: string }
      if (msg.type === 'joined') {
        ws.send(JSON.stringify({ type: 'hello', consent: true }))
      } else if (msg.type === 'ready') {
        try {
          const wl = (navigator as unknown as { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }).wakeLock
          try { lock.current = (await wl?.request('screen')) ?? null } catch { /* screen lock is a bonus, not a requirement */ }
          stopMic.current = await mic((chunk) => {
            if (ws.readyState !== WebSocket.OPEN) return
            ws.send(muted.current ? new ArrayBuffer(chunk.byteLength) : chunk)      // muted: send silence so timing stays right
          })
        } catch {
          ws.close()
          fail('mic')
          return
        }
        const began = Date.now()
        window.clearInterval(timer.current)
        timer.current = window.setInterval(() => setState((s) => ({ ...s, seconds: Math.floor((Date.now() - began) / 1000) })), 1000)
        setState((s) => ({ ...s, status: 'live' }))
      } else if (msg.type === 'ended') {
        finished.current = true
        cleanup()
        setState((s) => (s.status === 'error' ? s : { ...s, status: 'ended' }))
      } else if (msg.type === 'error') {
        fail('server', msg.message ?? null)
      }
    }
    ws.onerror = () => { if (!finished.current) fail('connection') }
    ws.onclose = () => { if (!finished.current) fail('connection') }
  }, [cleanup, createSocket, fail, mic])

  const toggleMute = useCallback(() => {
    muted.current = !muted.current
    setState((s) => ({ ...s, muted: muted.current }))
  }, [])

  const leave = useCallback(() => {
    const ws = socket.current
    cleanup()
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
    else setState((s) => ({ ...s, status: 'ended' }))
  }, [cleanup])

  const reset = useCallback(() => {
    finished.current = true
    cleanup()
    socket.current?.close()
    setState(INITIAL)
  }, [cleanup])

  return { state, join, toggleMute, leave, reset }
}
