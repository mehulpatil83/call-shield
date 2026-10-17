import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import * as api from '../api'
import { createPcmPlayer, type PcmPlayer } from '../live/player'
import { initialLive, reduceLive, type ServerMessage } from '../live/state'
import type { SpeechLang } from '../types'

export function receiveUrl(code: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/call/receive?code=${code}`
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

  const closePlayer = useCallback(() => { player.current?.close(); player.current = null }, [])
  useEffect(() => () => { closePlayer(); socket.current?.close() }, [closePlayer])

  const start = useCallback(async (language: SpeechLang, skipAudio: boolean, publicUrl: string | null) => {
    dispatch({ type: '_connecting' })
    setListening(false)
    try {
      const created = await makeCall(language, true, skipAudio, publicUrl)
      setInfo(created)
      const ws = createSocket(receiveUrl(created.code))
      ws.binaryType = 'arraybuffer'
      socket.current = ws
      ws.onmessage = (ev) => {
        if (typeof ev.data !== 'string') { player.current?.push(ev.data as ArrayBuffer); return }
        dispatch(JSON.parse(ev.data) as ServerMessage)
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

  return { state, info, listening, start, setListen, end, reset }
}
