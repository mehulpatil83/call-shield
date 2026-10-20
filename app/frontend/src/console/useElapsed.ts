import { useEffect, useRef, useState } from 'react'
import type { LiveState } from '../live/state'

/** Whole seconds since the call went live (a smooth clock; the analysis only reports time when new words arrive). */
export function useElapsed(status: LiveState['status']): number {
  const [sec, setSec] = useState(0)
  const started = useRef<number | null>(null)
  const running = status === 'live' || status === 'reconnecting' || status === 'stopping'
  useEffect(() => {
    if (['idle', 'connecting', 'waiting', 'joined'].includes(status)) { started.current = null; setSec(0) }
  }, [status])
  useEffect(() => {
    if (!running) return
    if (started.current === null) started.current = Date.now()
    const tick = () => setSec(Math.floor((Date.now() - (started.current as number)) / 1000))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [running])
  return sec
}
