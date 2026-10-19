import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import LiveView from '../components/LiveView'
import { STRINGS } from '../i18n'
import { initialLive, type LiveState } from '../live/state'
import { alertDeps, pickVoice, playTone, speakText } from './alertDeps'

const t = STRINGS.en
const hit = { category: 'otp_request', kind: 'request' as const, quote: 'share the otp', start: 7, end: 20, explanation: 'x', source: '' }
const warn = { category: 'warning_otp', kind: 'warning' as const, quote: 'never share', start: 0, end: 5, explanation: 'x', source: '' }
const pressure = { category: 'urgency', kind: 'pressure' as const, quote: 'right now', start: 30, end: 39, explanation: 'x', source: '' }
const base: LiveState = { ...initialLive, status: 'live', level: 'elevated', score: 4, seconds: 5, hits: [hit] }
const elevated: LiveState = { ...base, alert: 'elevated' }
const high: LiveState = { ...base, level: 'high', score: 8, alert: 'high', hits: [warn, pressure, hit] }

let tone: ReturnType<typeof vi.spyOn>
let speak: ReturnType<typeof vi.spyOn>
let stop: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  localStorage.clear()
  tone = vi.spyOn(alertDeps, 'playTone').mockImplementation(() => {})
  speak = vi.spyOn(alertDeps, 'speakText').mockReturnValue('spoken')
  stop = vi.spyOn(alertDeps, 'stopSpeaking').mockImplementation(() => {})
})
afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

const view = (state: LiveState, lang: keyof typeof STRINGS = 'en') =>
  <LiveView t={STRINGS[lang]} state={state} onOpenReport={() => {}} onAgain={() => {}} />

describe('alert experience', () => {
  it('elevated risk: an amber banner and one soft beep, no full screen and no speech', () => {
    render(view(elevated))
    expect(screen.getByTestId('alert-banner')).toHaveTextContent(t.alert.elevated)
    expect(screen.queryByTestId('alert-overlay')).toBeNull()
    expect(tone).toHaveBeenCalledTimes(1)
    expect(tone).toHaveBeenCalledWith('elevated')
    expect(speak).not.toHaveBeenCalled()
  })

  it('high risk: a full-screen warning with advice and the strongest evidence, a siren and spoken advice', () => {
    render(view(high))
    const dlg = screen.getByRole('alertdialog')
    expect(dlg).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('heading', { name: t.alert.headline })).toBeInTheDocument()
    expect(dlg).toHaveTextContent(t.advice.high[0])
    expect(dlg).toHaveTextContent('“share the otp”')                      // request first
    expect(dlg).toHaveTextContent('“right now”')
    expect(dlg).not.toHaveTextContent('never share')                      // a warning is not evidence of a scam
    expect(tone).toHaveBeenCalledWith('high')
    expect(speak).toHaveBeenCalledWith(t.alert.spoken, 'en')
    expect(document.title).toContain(t.alert.titleFlash)
    expect(screen.getByRole('button', { name: t.alert.dismiss })).toHaveFocus()
  })

  it('fires once: new evidence or a re-render does not beep or speak again', () => {
    const { rerender } = render(view(high))
    rerender(view({ ...high, seconds: 9, hits: [...high.hits, { ...hit, quote: 'otp again' }] }))
    rerender(view({ ...high, seconds: 12 }))
    expect(tone).toHaveBeenCalledTimes(1)
    expect(speak).toHaveBeenCalledTimes(1)
  })

  it('goes from the amber banner to the full-screen warning when the risk rises, with a single beep at each step', () => {
    const { rerender } = render(view(elevated))
    expect(tone).toHaveBeenCalledTimes(1)
    rerender(view(high))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(tone.mock.calls.map((c: unknown[]) => c[0])).toEqual(['elevated', 'high'])
    expect(speak).toHaveBeenCalledTimes(1)
  })

  it('a call that starts at high does not also play the elevated beep', () => {
    render(view(high))
    expect(tone.mock.calls.map((c: unknown[]) => c[0])).toEqual(['high'])
  })

  it('dismiss closes the warning, stops the voice and restores the page title', () => {
    const before = document.title
    render(view(high))
    fireEvent.click(screen.getByRole('button', { name: t.alert.dismiss }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(stop).toHaveBeenCalled()
    expect(document.title).toBe(before)
  })

  it('Escape dismisses', () => {
    render(view(high))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('"Say it again" speaks the advice again', () => {
    render(view(high))
    speak.mockClear()
    fireEvent.click(screen.getByRole('button', { name: t.alert.repeat }))
    expect(speak).toHaveBeenCalledWith(t.alert.spoken, 'en')
  })

  it('a new call (idle or connecting) re-arms the alert', () => {
    const { rerender } = render(view(high))
    fireEvent.click(screen.getByRole('button', { name: t.alert.dismiss }))
    rerender(view({ ...initialLive, status: 'connecting' }))
    rerender(view(high))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(tone).toHaveBeenCalledTimes(2)
  })

  it('never covers the report: the warning closes when the call ends', () => {
    const { rerender } = render(view(high))
    rerender(view({ ...high, status: 'ended', id: 'abcdef012345' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('speaks in the interface language', () => {
    render(view(high, 'hi'))
    expect(speak).toHaveBeenCalledWith(STRINGS.hi.alert.spoken, 'hi')
    expect(screen.getByRole('heading', { name: STRINGS.hi.alert.headline })).toBeInTheDocument()
  })

  it('says so when this device has no voice for the language', () => {
    speak.mockReturnValue('unavailable')
    render(view(high, 'mr'))
    expect(screen.getByRole('note')).toHaveTextContent(STRINGS.mr.alert.noVoice)
  })
})

describe('alert settings', () => {
  it('sound off: no beep. voice off: no speech. Both are remembered', () => {
    localStorage.setItem('cs-alert', JSON.stringify({ sound: false, voice: false, fullscreen: true }))
    render(view(high))
    expect(tone).not.toHaveBeenCalled()
    expect(speak).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: t.alert.repeat })).toBeNull()
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  })

  it('full screen off: a red banner instead of the overlay', () => {
    localStorage.setItem('cs-alert', JSON.stringify({ sound: true, voice: true, fullscreen: false }))
    render(view(high))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(screen.getByTestId('alert-banner')).toHaveClass('high')
    expect(tone).toHaveBeenCalledWith('high')
  })

  it('the settings panel saves choices and shows the echo warning', () => {
    render(view({ ...initialLive, status: 'live' }))
    fireEvent.click(screen.getByText(t.alert.settings))
    expect(screen.getByText(t.alert.echoNote)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(t.alert.voice))
    fireEvent.click(screen.getByLabelText(t.alert.sound))
    expect(JSON.parse(localStorage.getItem('cs-alert')!)).toEqual({ sound: false, voice: false, fullscreen: true })
  })
})

describe('sound and speech helpers', () => {
  const v = (lang: string) => ({ lang })
  it('picks the best voice and falls back sensibly', () => {
    expect(pickVoice([v('en-US'), v('hi-IN'), v('en-IN')], 'en')).toEqual(v('en-IN'))
    expect(pickVoice([v('en-US')], 'en')).toEqual(v('en-US'))
    expect(pickVoice([v('hi_IN')], 'hi')).toEqual(v('hi_IN'))
    expect(pickVoice([v('en-US'), v('hi-IN')], 'mr')).toEqual(v('hi-IN'))      // Marathi falls back to Hindi
    expect(pickVoice([v('en-US')], 'hi')).toBeUndefined()
  })

  it('does not read Hindi or Marathi with an English voice, but trusts the browser while the voice list is still empty', () => {
    vi.stubGlobal('SpeechSynthesisUtterance', class { text: string; lang = ''; voice: unknown; rate = 1; constructor(x: string) { this.text = x } })
    const synth = (voices: { lang: string }[]) => ({ getVoices: () => voices, speak: vi.fn(), cancel: vi.fn() })
    const a = synth([v('en-US')])
    expect(speakText('x', 'hi', a)).toBe('unavailable')
    expect(a.speak).not.toHaveBeenCalled()
    const b = synth([])
    expect(speakText('x', 'hi', b)).toBe('spoken')
    expect(b.speak).toHaveBeenCalledTimes(1)
    const c = synth([v('hi-IN')])
    expect(speakText('x', 'mr', c)).toBe('spoken')
    expect(c.cancel).toHaveBeenCalled()                                        // it never talks over itself
    expect(speakText('x', 'en', undefined)).toBe('unavailable')
    vi.unstubAllGlobals()
  })

  it('playTone generates a siren with no audio files and closes the audio context afterwards', () => {
    vi.useFakeTimers()
    const started: number[] = []
    class FakeCtx {
      currentTime = 0; destination = {}; close = vi.fn()
      createGain() { return { gain: { value: 0 }, connect: vi.fn() } }
      createOscillator() { return { type: '', frequency: { value: 0 }, connect: vi.fn(), start: (at: number) => started.push(at), stop: vi.fn() } }
    }
    vi.stubGlobal('AudioContext', FakeCtx)
    playTone('high')
    expect(started).toHaveLength(4)
    playTone('elevated')
    expect(started).toHaveLength(5)
    act(() => { vi.advanceTimersByTime(3000) })
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('has the alert texts in every language', () => {
    const keys = Object.keys(STRINGS.en.alert).sort()
    for (const lang of ['hi', 'mr'] as const) {
      expect(Object.keys(STRINGS[lang].alert).sort()).toEqual(keys)
      for (const k of keys) expect((STRINGS[lang].alert as unknown as Record<string, string>)[k].trim(), `${lang}:${k}`).not.toBe('')
      expect(STRINGS[lang].code).toBe(lang)
    }
  })
})
