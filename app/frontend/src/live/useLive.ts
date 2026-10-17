import { useCallback, useEffect, useReducer, useRef } from 'react'
import type { SpeechLang } from '../types'
import { startMicrophone, startReplay } from './audio'
import { initialLive, reduceLive, type ServerMessage } from './state'

export function liveUrl(language: SpeechLang, skipAudio: boolean): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/live?language=${language}&consent=true&skip_audio_check=${skipAudio}`
}

export function useLive(createSocket: (url: string) => WebSocket = (u) => new WebSocket(u)) {
  const [state, dispatch] = useReducer(reduceLive, initialLive)
  const socket = useRef<WebSocket | null>(null)
  const stopAudio = useRef<(() => void) | null>(null)

  const cleanup = useCallback(() => {
    stopAudio.current?.()
    stopAudio.current = null
  }, [])

  useEffect(() => () => { cleanup(); socket.current?.close() }, [cleanup])

  const open = useCallback((language: SpeechLang, skipAudio: boolean, begin: (send: (b: ArrayBuffer) => void, finish: () => void) => Promise<() => void>) => {
    dispatch({ type: '_connecting' })
    const ws = createSocket(liveUrl(language, skipAudio))
    ws.binaryType = 'arraybuffer'
    socket.current = ws
    const finish = () => {
      dispatch({ type: '_stopping' })
      cleanup()
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
    }
    ws.onmessage = async (ev) => {
      const msg = JSON.parse(ev.data as string) as ServerMessage
      dispatch(msg)
      if (msg.type === 'ready') {
        try {
          stopAudio.current = await begin((b) => { if (ws.readyState === WebSocket.OPEN) ws.send(b) }, finish)
        } catch (e) {
          dispatch({ type: 'error', message: e instanceof Error ? e.message : String(e) })
          ws.close()
        }
      }
    }
    ws.onerror = () => dispatch({ type: 'error', message: 'Connection problem.' })
    ws.onclose = () => cleanup()
  }, [cleanup, createSocket])

  const startMic = useCallback((language: SpeechLang, skipAudio: boolean) =>
    open(language, skipAudio, (send) => startMicrophone(send)), [open])
  const replay = useCallback((file: File, language: SpeechLang, skipAudio: boolean) =>
    open(language, skipAudio, (send, finish) => startReplay(file, send, finish)), [open])
  const stop = useCallback(() => {
    dispatch({ type: '_stopping' })
    cleanup()
    const ws = socket.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
  }, [cleanup])
  const reset = useCallback(() => { cleanup(); socket.current?.close(); dispatch({ type: '_reset' }) }, [cleanup])

  return { state, startMic, replay, stop, reset }
}
