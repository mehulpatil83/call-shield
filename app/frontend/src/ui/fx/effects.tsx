import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Level } from '../../types'
import { prefersReducedMotion } from '../useAnimatedNumber'

/** How much of the WebGL decoration is drawn: everything, a quiet version (nothing moves by itself), or none. */
export type FxMode = 'full' | 'reduced' | 'off'

interface Fx {
  mode: FxMode
  setMode: (m: FxMode) => void
  /** true when the app lowered the effects itself because the screen was too slow */
  autoReduced: boolean
  degrade: () => void
  /** the risk level the page is "in" right now: the background and the foil follow it */
  level: Level
  setLevel: (l: Level) => void
}

const noop = () => {}
const DEFAULT: Fx = { mode: 'full', setMode: noop, autoReduced: false, degrade: noop, level: 'low', setLevel: noop }
const Ctx = createContext<Fx>(DEFAULT)
const KEY = 'cs-fx'
const store = {
  get: () => { try { return localStorage.getItem(KEY) } catch { return null } },
  set: (v: string) => { try { localStorage.setItem(KEY, v) } catch { /* storage may be unavailable */ } },
}

function initialMode(): FxMode {
  const saved = store.get()
  if (saved === 'full' || saved === 'reduced' || saved === 'off') return saved
  return prefersReducedMotion() ? 'reduced' : 'full'
}

export function EffectsProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<FxMode>(initialMode)
  const [autoReduced, setAuto] = useState(false)
  const [level, setLevel] = useState<Level>('low')
  const setMode = useCallback((m: FxMode) => { setModeState(m); setAuto(false); store.set(m) }, [])
  const degrade = useCallback(() => {
    setModeState((m) => (m === 'full' ? 'reduced' : m === 'reduced' ? 'off' : m))
    setAuto(true)
  }, [])
  useEffect(() => { if (autoReduced) store.set(mode) }, [autoReduced, mode])           // a slow screen stays reduced next time
  const value = useMemo(() => ({ mode, setMode, autoReduced, degrade, level, setLevel }), [mode, setMode, autoReduced, degrade, level])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useFx = () => useContext(Ctx)
export const useFps = useFx

/** A page that knows the current risk calls this, so the background and the phone foil take on its colour. */
export function useAtmosphere(level: Level) {
  const { setLevel } = useFx()
  useEffect(() => {
    setLevel(level)
    return () => setLevel('low')
  }, [level, setLevel])
}

/** Dark or light colour scheme of the system (dark when it cannot be asked). */
export function useDarkScheme(): boolean {
  const query = typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null
  const [dark, setDark] = useState(query ? query.matches : true)
  useEffect(() => {
    if (!query) return
    const on = (e: MediaQueryListEvent) => setDark(e.matches)
    query.addEventListener?.('change', on)
    return () => query.removeEventListener?.('change', on)
  }, [query])
  return dark
}

/** Measures the frame rate for three seconds (after a short settle) and calls onSlow when it is below `minFps`. Runs again when `active` or `again` change. */
export function useFpsWatchdog(active: boolean, minFps: number, onSlow: () => void, again: string = '') {
  useEffect(() => {
    if (!active || typeof requestAnimationFrame === 'undefined') return
    let raf = 0, frames = 0, start = 0, stopped = false
    const restart = () => { frames = 0; start = 0 }
    const loop = (t: number) => {
      if (stopped) return
      if (document.hidden) restart()
      else {
        if (!start) start = t
        frames += 1
        const elapsed = t - start
        if (elapsed >= 3000) {
          if (frames / (elapsed / 1000) < minFps) onSlow()
          return
        }
      }
      raf = requestAnimationFrame(loop)
    }
    const timer = window.setTimeout(() => { raf = requestAnimationFrame(loop) }, 2000)
    document.addEventListener('visibilitychange', restart)
    return () => { stopped = true; window.clearTimeout(timer); cancelAnimationFrame(raf); document.removeEventListener('visibilitychange', restart) }
  }, [active, minFps, onSlow, again])         // `again` (the current mode) makes it measure once more after every change
}
