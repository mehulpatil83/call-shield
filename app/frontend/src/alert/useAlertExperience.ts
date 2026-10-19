import { useCallback, useEffect, useRef, useState } from 'react'
import type { Dict } from '../i18n'
import type { LiveState } from '../live/state'
import { alertDeps, type SpeakResult } from './alertDeps'

export interface AlertSettings { sound: boolean; voice: boolean; fullscreen: boolean }
const DEFAULTS: AlertSettings = { sound: true, voice: true, fullscreen: true }
const KEY = 'cs-alert'

export function loadSettings(): AlertSettings {
  try { return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<AlertSettings>) } } catch { return DEFAULTS }
}

/** Beep, spoken advice and a full-screen warning, once per call at each step up: elevated, then high. */
export function useAlertExperience(t: Dict, state: Pick<LiveState, 'alert' | 'status'>) {
  const [settings, setSettings] = useState<AlertSettings>(loadSettings)
  const [shown, setShown] = useState<'none' | 'elevated' | 'high'>('none')
  const [voice, setVoice] = useState<SpeakResult | null>(null)
  const fired = useRef({ elevated: false, high: false })
  const live = useRef(settings)
  live.current = settings

  const change = useCallback((patch: Partial<AlertSettings>) => {
    setSettings((s) => {
      const next = { ...s, ...patch }
      try { localStorage.setItem(KEY, JSON.stringify(next)) } catch { /* not remembered: fine */ }
      return next
    })
  }, [])

  useEffect(() => {
    const { status, alert } = state
    if (status === 'idle' || status === 'connecting') {          // a new call: forget the last one
      fired.current = { elevated: false, high: false }
      setShown('none')
      setVoice(null)
      return
    }
    if (status === 'ended' || status === 'error') {              // never cover the report
      setShown('none')
      alertDeps.stopSpeaking()
      return
    }
    if (alert === 'high' && !fired.current.high) {
      fired.current = { elevated: true, high: true }
      setShown('high')
      if (live.current.sound) alertDeps.playTone('high')
      setVoice(live.current.voice ? alertDeps.speakText(t.alert.spoken, t.code) : null)
    } else if (alert === 'elevated' && !fired.current.elevated && !fired.current.high) {
      fired.current.elevated = true
      setShown('elevated')
      if (live.current.sound) alertDeps.playTone('elevated')
    }
  }, [state, t])

  const dismiss = useCallback(() => { alertDeps.stopSpeaking(); setShown('none') }, [])
  const repeat = useCallback(() => setVoice(alertDeps.speakText(t.alert.spoken, t.code)), [t])

  // the tab title warns even when this tab is in the background
  useEffect(() => {
    if (shown !== 'high') return
    const before = document.title
    document.title = `⚠ ${t.alert.titleFlash}`
    return () => { document.title = before }
  }, [shown, t])

  useEffect(() => () => alertDeps.stopSpeaking(), [])
  return { shown, settings, change, dismiss, repeat, voice }
}
