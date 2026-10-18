import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import * as api from '../api'
import { createPcmPlayer, type PcmPlayer } from '../live/player'
import { initialLive, reduceLive, type ServerMessage } from '../live/state'
import type { SpeechLang } from '../types'

export function receiveUrl(code: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/call/receive?code=${code}`
}

export type AudioState = 'none' | 'silent' | 'ok'
export const AUDIO_STALE_MS = 3_000      // no audio message for this long: nothing is arriving
export const AUDIO_QUIET_MS = 5_000      // audio is arriving but has been silent for this long
export const AUDIO_QUIET_RMS = 0.004

/** What the Receiver should tell the user about the incoming audio. Pure, so it is easy to test. */
export function audioStatus(now: number, lastAudioAt: number, lastLoudAt: number): AudioState {
  if (lastAudioAt === 0 || now - lastAudioAt > AUDIO_STALE_MS) return 'none'
  if (now - lastLoudAt > AUDIO_QUIET_MS) return 'silent'
  return 'ok'
}

export interface ReceiverDeps {
  createSocket?: (url: string) => WebSocket
  createCall?: typeof api.createCall
  createPlayer?: () => PcmPlayer
}

/** The Receiver side of a call: creates the call, waits for the Speaker, and turns server messages into live-check state. */
export function useCallReceiver(deps: ReceiverDeps = {}) {
  const createSocket = deps.createSocket ?? ((u: string) => new WebSocket(u))
  const makeCall = deps.createCall ?? api.createCall
  const makePlayer = deps.createPlayer ?? createPcmPlayer
  const [state, dispatch] = useReducer(reduceLive, initialLive)
  const [info, setInfo] = useState<api.CallCreated | null>(null)
  const [listening, setListening] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  const player = useRef<PcmPlayer | null>(null)
  const [audio, setAudio] = useState<{ state: AudioState; level: number }>({ state: 'none', level: 0 })
  const lastAudio = useRef(0)
  const lastLoud = useRef(0)

  useEffect(() => {
    const id = window.setInterval(() => {
      setAudio((a) => {
        const st = audioStatus(Date.now(), lastAudio.current, lastLoud.current)
        return st === a.state ? a : { state: st, level: st === 'ok' ? a.level : 0 }
      })
    }, 1000)
    return () => window.clearInterval(id)
  }, [])

  const closePlayer = useCallback(() => { player.current?.close(); player.current = null }, [])
  useEffect(() => () => { closePlayer(); socket.current?.close() }, [closePlayer])

  const start = useCallback(async (language: SpeechLang, skipAudio: boolean, publicUrl: string | null) => {
    dispatch({ type: '_connecting' })
    setListening(false)
    lastAudio.current = 0
    lastLoud.current = 0
    setAudio({ state: 'none', level: 0 })
    try {
      const created = await makeCall(language, true, skipAudio, publicUrl)
      setInfo(created)
      const ws = createSocket(receiveUrl(created.code))
      ws.binaryType = 'arraybuffer'
      socket.current = ws
      ws.onmessage = (ev) => {
        if (typeof ev.data !== 'string') { player.current?.push(ev.data as ArrayBuffer); return }
        const msg = JSON.parse(ev.data) as ServerMessage | { type: 'audio'; rms: number }
        if (msg.type === 'audio') {                         // "audio is arriving, this loud": not part of the analysis state
          const now = Date.now()
          lastAudio.current = now
          if (msg.rms > AUDIO_QUIET_RMS || lastLoud.current === 0) lastLoud.current = now
          setAudio({ state: audioStatus(now, lastAudio.current, lastLoud.current), level: Math.min(1, msg.rms * 5) })
          return
        }
        dispatch(msg)
      }
      ws.onerror = () => dispatch({ type: 'error', message: 'Connection problem.' })
    } catch (e) {
      dispatch({ type: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [createSocket, makeCall])

  /** Must be called from a click: browsers only allow sound after a user gesture. */
  const setListen = useCallback((on: boolean) => {
    if (on && !player.current) player.current = makePlayer()
    if (!on) closePlayer()
    setListening(on)
    const ws = socket.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'listen', on }))
  }, [closePlayer, makePlayer])

  const end = useCallback(() => {
    dispatch({ type: '_stopping' })
    const ws = socket.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'end' }))
  }, [])

  const reset = useCallback(() => {
    closePlayer()
    socket.current?.close()
    socket.current = null
    setInfo(null)
    setListening(false)
    dispatch({ type: '_reset' })
  }, [closePlayer])

  return { state, info, listening, audio, start, setListen, end, reset }
}
