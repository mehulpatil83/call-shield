import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import { alertDeps } from '../alert/alertDeps'
import { STRINGS } from '../i18n'
import { initialLive, reduceLive, type LiveAction, type LiveState } from '../live/state'
import type { Hit } from '../types'
import CallReceiver from '../components/CallReceiver'
import CallConsole from './CallConsole'
import { TACTICS, estimateRupees, formatClock, scorecard, wantsNow } from './derive'
import RiskGraph from './RiskGraph'

const t = STRINGS.en
const TEXT = 'i am from your bank security department please share the otp right now'
// offsets are computed from the text so they can never drift; a phrase that is not in the text gets start -1 and is not drawn
const h = (category: string, kind: Hit['kind'], quote: string): Hit => { const start = TEXT.indexOf(quote); return { category, kind, quote, start, end: start + quote.length, explanation: 'x', source: '' } }
const AUTH = h('authority', 'context', 'bank security department')
const OTP = h('otp_request', 'request', 'share the otp')
const NOW = h('urgency', 'pressure', 'right now')
const WARN = h('warning_otp', 'warning', 'never share')
const analysis = (seconds: number, score: number, level: 'low' | 'elevated' | 'high', hits: Hit[]): LiveAction => ({
  type: 'analysis', level, score, summary: '', seconds, hits, tracks: [{ code: 'en-IN', text: TEXT, hits }],
})
const run = (...msgs: LiveAction[]): LiveState => msgs.reduce(reduceLive, { ...initialLive, status: 'live' } as LiveState)

const call = run(
  analysis(6, 2, 'low', [AUTH]),
  analysis(14, 5, 'elevated', [AUTH, NOW]), { type: 'alert', level: 'elevated' },
  analysis(22, 8, 'high', [AUTH, NOW, OTP, WARN]), { type: 'alert', level: 'high' },
)

let tone: ReturnType<typeof vi.spyOn>
beforeEach(() => {
  localStorage.clear()
  tone = vi.spyOn(alertDeps, 'playTone').mockImplementation(() => {})
  vi.spyOn(alertDeps, 'speakText').mockReturnValue('spoken')
  vi.spyOn(alertDeps, 'stopSpeaking').mockImplementation(() => {})
})
afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

const consoleView = (state: LiveState, over: Partial<Parameters<typeof CallConsole>[0]> = {}) => (
  <CallConsole t={t} state={state} language="en" listening={false} audio={{ state: 'ok', level: 0.2 }}
               onListen={() => {}} onEnd={() => {}} onAgain={() => {}} onOpenReport={() => {}} {...over} />
)

describe('live state: history and events', () => {
  it('records a graph point per update, tactics once with the time first heard, and alerts', () => {
    expect(call.history.map((p) => [p.t, p.score, p.level])).toEqual([[6, 2, 'low'], [14, 5, 'elevated'], [22, 8, 'high']])
    expect(call.events.map((e) => e.id)).toEqual(['tactic-authority', 'tactic-urgency', 'alert-elevated', 'tactic-otp_request', 'alert-high'])
    expect(call.events[1]).toMatchObject({ t: 14, hitKind: 'pressure', quote: 'right now' })
    expect(call.history[2].fresh).toEqual([{ category: 'otp_request', quote: 'share the otp' }])     // only what is new at this step
    expect(call.history[1].fresh.map((f) => f.category)).toEqual(['urgency'])
  })

  it('ignores cautions, repeated tactics and repeated alerts', () => {
    const s = run(analysis(5, 1, 'low', [WARN]), analysis(8, 2, 'low', [AUTH]), analysis(9, 2, 'low', [AUTH]), { type: 'alert', level: 'high' }, { type: 'alert', level: 'high' })
    expect(s.events.map((e) => e.id)).toEqual(['tactic-authority', 'alert-high'])
    expect(s.events[1].t).toBe(9)
  })

  it('keeps the final level of the whole call when it ends', () => {
    expect(reduceLive(call, { type: 'ended', id: 'abcdef012345', level: 'low', max_level: 'high' }).finalLevel).toBe('high')
    expect(reduceLive(call, { type: 'ended', id: null }).finalLevel).toBe('high')          // falls back to the current level
    expect(reduceLive(call, { type: '_connecting' }).history).toEqual([])                     // a new call starts clean
  })

  it('caps the history', () => {
    let s = run()
    for (let i = 0; i < 700; i++) s = reduceLive(s, analysis(i, 1, 'low', []))
    expect(s.history).toHaveLength(600)
  })
})

describe('derived facts', () => {
  it('builds the scorecard from the events', () => {
    const c = scorecard({ ...call, finalLevel: 'high' })
    expect(c).toMatchObject({ verdict: 'high', peakScore: 8, firstWarningAt: 14, highAlertAt: 22, firstRequestAt: 22, duration: 22 })
    expect(c.tactics).toEqual(['authority', 'urgency', 'otp_request'])
  })

  it('has nothing to report for a calm call', () => {
    const c = scorecard(run(analysis(5, 0, 'low', [])))
    expect(c).toMatchObject({ verdict: 'low', firstWarningAt: null, highAlertAt: null, firstRequestAt: null, tactics: [] })
  })

  it('lists what the caller wants, newest first, and estimates cost by number of streams', () => {
    expect(wantsNow(call.events)).toEqual(['otp_request'])
    expect(formatClock(75)).toBe('1:15')
    expect(formatClock(-3)).toBe('0:00')
    expect(estimateRupees(60, 'en')).toBeCloseTo(0.47, 2)
    expect(estimateRupees(60, 'hinglish')).toBeCloseTo(0.94, 2)
  })

  it('every tactic has a label and an explanation in every language, and a "wants" line when it is a request', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      for (const k of TACTICS) {
        expect(STRINGS[lang].categories[k.id], `${lang}:${k.id}`).toBeTruthy()
        if (k.kind === 'request') expect(STRINGS[lang].console.wants[k.id], `${lang}:wants:${k.id}`).toBeTruthy()
      }
    }
  })

  it('has every console text in every language', () => {
    const keys = Object.keys(STRINGS.en.console).sort()
    for (const lang of ['hi', 'mr'] as const) {
      const c = STRINGS[lang].console as unknown as Record<string, unknown>
      expect(Object.keys(c).sort()).toEqual(keys)
      for (const k of keys) {
        const v = c[k]
        if (typeof v === 'function') expect((v as (a: never, b: never) => string)(5 as never, 7 as never).length, `${lang}:${k}`).toBeGreaterThan(0)
        else if (typeof v === 'string') expect(v.trim(), `${lang}:${k}`).not.toBe('')
      }
      expect(Object.keys(STRINGS[lang].console.wants).sort()).toEqual(Object.keys(STRINGS.en.console.wants).sort())
    }
  })
})

describe('RiskGraph', () => {
  it('says it is waiting before there is data', () => {
    render(<RiskGraph t={t} history={[]} events={[]} level="low" score={0} />)
    expect(screen.getByText(t.console.graphEmpty)).toBeInTheDocument()
  })

  it('draws the line, the alert markers and an accessible summary', () => {
    const { container } = render(<RiskGraph t={t} history={call.history} events={call.events} level="high" score={8} />)
    expect(screen.getByRole('img', { name: t.console.graphLabel(t.levels.high, 8) })).toBeInTheDocument()
    expect(container.querySelectorAll('line.seg')).toHaveLength(2)
    expect(container.querySelector('line.seg.high')).not.toBeNull()
    expect(screen.getByTestId('marker-elevated')).toHaveTextContent(t.console.markerElevated)
    expect(screen.getByTestId('marker-high')).toHaveTextContent(t.console.markerHigh)
    expect(screen.getAllByTestId('graph-point')).toHaveLength(3)
  })

  it('shows what was heard at a point on hover or focus, and says so when nothing new was flagged', () => {
    render(<RiskGraph t={t} history={[...call.history, { t: 30, score: 8, level: 'high', fresh: [] }]} events={call.events} level="high" score={8} />)
    const pts = screen.getAllByTestId('graph-point')
    expect(screen.queryByTestId('graph-tip')).toBeNull()
    fireEvent.mouseEnter(pts[2])
    expect(screen.getByTestId('graph-tip')).toHaveTextContent('0:22')
    expect(screen.getByTestId('graph-tip')).toHaveTextContent('“share the otp”')
    expect(screen.getByTestId('graph-tip')).toHaveTextContent(t.categories.otp_request.label)
    fireEvent.focus(pts[3])
    expect(screen.getByTestId('graph-tip')).toHaveTextContent(t.console.noNewEvidence)
    fireEvent.blur(pts[3])
    expect(screen.queryByTestId('graph-tip')).toBeNull()
  })

  it('stretches the time axis as the call gets longer', () => {
    const long = [{ t: 200, score: 3, level: 'low' as const, fresh: [] }]
    const { container } = render(<RiskGraph t={t} history={long} events={[]} level="low" score={3} />)
    const labels = [...container.querySelectorAll('text.axis')].map((n) => n.textContent)
    expect(labels).toEqual(['0', '5', '10', '0:00', '1:00', '2:00', '3:00', '4:00'])      // a call over 150 s labels every minute
  })
})

describe('CallConsole', () => {
  it('shows both halves: live analysis on the left, the phone on the right', () => {
    render(consoleView(call))
    const phone = screen.getByTestId('phone')
    expect(screen.getByTestId('risk-graph')).toBeInTheDocument()
    expect(screen.getByRole('meter', { name: t.live.meter })).toHaveAttribute('aria-valuenow', '8')
    expect(screen.getByTestId('console-state')).toHaveTextContent(t.console.live)
    expect(within(phone).getByText(t.console.unknownCaller)).toBeInTheDocument()
    expect(within(phone).getByTestId('phone-risk')).toHaveTextContent(t.levels.high)
    expect(phone.contains(screen.getByTestId('risk-graph'))).toBe(false)
  })

  it('lights the risky words in the phone captions', () => {
    render(consoleView(call, {}))
    const caps = screen.getByTestId('phone-captions')
    const marks = [...caps.querySelectorAll('mark')].map((m) => [m.className, m.textContent])
    expect(marks).toEqual([['mark context', 'bank security department'], ['mark request', 'share the otp'], ['mark pressure', 'right now']])
    expect(caps.textContent).toBe(TEXT)                                         // the captions always read as the original words
  })

  it('at high risk the warning takes over the phone, not the whole page; dismiss closes it', () => {
    render(consoleView(call))
    const take = screen.getByTestId('phone-takeover')
    expect(screen.getByTestId('phone')).toContainElement(take)
    expect(take).toHaveTextContent(t.alert.headline)
    expect(take).toHaveTextContent(t.advice.high[0])
    expect(take).toHaveTextContent('“share the otp”')
    expect(screen.queryByTestId('alert-overlay')).toBeNull()
    expect(tone.mock.calls.map((c: unknown[]) => c[0])).toEqual(['high'])
    fireEvent.click(within(take).getByRole('button', { name: t.alert.dismiss }))
    expect(screen.queryByTestId('phone-takeover')).toBeNull()
    expect(screen.getByTestId('live-alert')).toHaveTextContent(t.live.alertHigh)                  // the left side keeps showing it
  })

  it('at elevated risk the phone shows a small amber strip, and with takeover switched off so does high', () => {
    const { unmount } = render(consoleView(run(analysis(14, 5, 'elevated', [AUTH, NOW]), { type: 'alert', level: 'elevated' })))
    expect(screen.getByTestId('phone-strip')).toHaveTextContent(t.console.phoneElevated)
    expect(screen.queryByTestId('phone-takeover')).toBeNull()
    unmount()
    localStorage.setItem('cs-alert', JSON.stringify({ sound: false, voice: false, fullscreen: false }))
    render(consoleView(call))
    expect(screen.queryByTestId('phone-takeover')).toBeNull()
    expect(screen.getByTestId('phone-strip')).toBeInTheDocument()
  })

  it('has working phone buttons', () => {
    const onListen = vi.fn(), onEnd = vi.fn()
    render(consoleView(run(analysis(6, 2, 'low', [AUTH])), { onListen, onEnd }))
    fireEvent.click(screen.getByRole('button', { name: t.console.speaker }))
    expect(onListen).toHaveBeenCalledWith(true)
    fireEvent.click(screen.getByRole('button', { name: t.console.hangUp }))
    expect(onEnd).toHaveBeenCalledTimes(1)
  })

  it('explains what the caller wants and which tactics were heard', () => {
    render(consoleView(call))
    expect(screen.getByTestId('wants')).toHaveTextContent(t.console.wants.otp_request)
    const on = [...screen.getByTestId('tactics').querySelectorAll('li[data-on="true"]')].map((n) => n.textContent)
    expect(on).toEqual([t.categories.otp_request.label, t.categories.urgency.label, t.categories.authority.label])
    expect(screen.getByTestId('live-advice')).toHaveTextContent(t.advice.high[0])
  })

  it('says nothing was asked for when nothing was', () => {
    render(consoleView(run(analysis(6, 1, 'low', [AUTH]))))
    expect(screen.getByTestId('wants-none')).toHaveTextContent(t.console.wantsNothing)
  })

  it('selecting a timeline item lights those words in the captions and explains why they matter', () => {
    render(consoleView(call))
    const items = within(screen.getByTestId('timeline')).getAllByRole('button')
    expect(items).toHaveLength(5)
    expect(items[0]).toHaveTextContent('0:06')
    expect(screen.queryByTestId('why')).toBeNull()
    fireEvent.click(items[3])                                                   // the OTP request
    expect(items[3]).toHaveAttribute('aria-pressed', 'true')
    const focused = screen.getByTestId('phone-captions').querySelectorAll('mark.focus')
    expect([...focused].map((m) => m.textContent)).toEqual(['share the otp'])
    expect(screen.getByTestId('why')).toHaveTextContent(t.categories.otp_request.explain)
    fireEvent.click(items[2])                                                   // an alert item: no words to light
    expect(screen.getByTestId('phone-captions').querySelectorAll('mark.focus')).toHaveLength(0)
    expect(screen.getByTestId('why')).toHaveTextContent(t.live.alertElevated)
    fireEvent.click(items[2])
    expect(screen.queryByTestId('why')).toBeNull()
  })

  it('shows the scorecard after the call, with the measured times', () => {
    const done = reduceLive(call, { type: 'ended', id: 'abcdef012345', level: 'high', max_level: 'high' })
    const onOpen = vi.fn()
    render(consoleView(done, { onOpenReport: onOpen }))
    expect(screen.getByTestId('console-state')).toHaveTextContent(t.console.ended)
    expect(screen.getByTestId('sc-verdict')).toHaveTextContent(t.levels.high)
    expect(screen.getByTestId('sc-warning')).toHaveTextContent(t.console.after(14))
    expect(screen.getByTestId('sc-high')).toHaveTextContent(t.console.after(22))
    expect(screen.getByTestId('sc-ask')).toHaveTextContent(t.console.after(22))
    expect(screen.getByTestId('sc-tactics')).toHaveTextContent(t.categories.authority.label)
    expect(screen.getByTestId('phone-time')).toHaveTextContent(t.console.callEnded)
    expect(screen.queryByRole('alertdialog')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: t.live.openReport }))
    expect(onOpen).toHaveBeenCalledWith('abcdef012345')
  })

  it('a calm call gets a calm scorecard', () => {
    const done = reduceLive(run(analysis(10, 0, 'low', [])), { type: 'ended', id: 'abcdef012345', max_level: 'low' })
    render(consoleView(done))
    expect(screen.getByTestId('sc-verdict')).toHaveTextContent(t.levels.low)
    expect(screen.getByTestId('sc-high')).toHaveTextContent(t.console.notReached)
    expect(screen.getByTestId('sc-tactics')).toHaveTextContent(t.console.noTactics)
  })

  it('estimates the cost from the call length and the number of speech streams', () => {
    const long = run(analysis(60, 1, 'low', []))
    const { unmount } = render(consoleView(long))
    expect(screen.getByTestId('cost')).toHaveTextContent('₹0.47')
    unmount()
    render(consoleView(long, { language: 'hinglish' }))
    expect(screen.getByTestId('cost')).toHaveTextContent('₹0.94')
  })

  it('lists the demo scripts and copies one', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    render(consoleView(run()))
    const drawer = screen.getByTestId('presenter')
    expect(drawer).toHaveTextContent(t.console.scriptScam)
    expect(drawer).toHaveTextContent(t.console.scriptWarning)
    expect(drawer.querySelectorAll('.script')).toHaveLength(4)
    fireEvent.click(within(drawer).getAllByRole('button', { name: t.console.copy })[0])
    await screen.findByText(t.console.copied)
    expect(writeText.mock.calls[0][0]).toContain('fraud prevention team')
    vi.unstubAllGlobals()
  })

  it('works in Hindi and Marathi', () => {
    for (const lang of ['hi', 'mr'] as const) {
      const { unmount } = render(<CallConsole t={STRINGS[lang]} state={call} language="en" listening={false} audio={{ state: 'ok', level: 0.1 }}
                                              onListen={() => {}} onEnd={() => {}} onAgain={() => {}} onOpenReport={() => {}} />)
      expect(screen.getByTestId('phone-takeover')).toHaveTextContent(STRINGS[lang].alert.headline)
      expect(screen.getByTestId('wants')).toHaveTextContent(STRINGS[lang].console.wants.otp_request)
      unmount()
    }
  })

  it('shows the reconnecting banner on the console and on the phone', () => {
    render(consoleView({ ...call, status: 'reconnecting' }))
    expect(screen.getByTestId('call-reconnecting')).toBeInTheDocument()
    expect(screen.getByTestId('phone-time')).toHaveTextContent(t.console.reconnectingPhone)
  })
})

describe('CallReceiver switches to the console', () => {
  const created = { code: '482913', language: 'en', public_url: 'https://x.trycloudflare.com', join_url: 'https://x.trycloudflare.com/#/join/482913', expires_in: 600 }
  class Sock {
    static last: Sock | null = null
    binaryType = 'blob'; readyState = 1; onmessage: ((e: { data: unknown }) => void) | null = null; onerror = null; onclose = null
    constructor(public url: string) { Sock.last = this }
    send() {} close() {}
    push(m: object) { this.onmessage?.({ data: JSON.stringify(m) }) }
  }

  it('shows the form and the demo scripts before the call, and only the console while it runs', async () => {
    render(<CallReceiver t={t} onOpenReport={() => {}} loadConfig={async () => ({ public_url: null })}
                         deps={{ createSocket: (u) => new Sock(u) as unknown as WebSocket, createCall: vi.fn().mockResolvedValue(created) }} />)
    expect(screen.getByRole('heading', { name: t.call.title })).toBeInTheDocument()
    expect(screen.getByTestId('presenter')).toBeInTheDocument()
    expect(screen.queryByTestId('console')).toBeNull()
    fireEvent.click(screen.getByLabelText(t.call.consent))
    fireEvent.click(screen.getByRole('button', { name: t.call.start }))
    await screen.findByTestId('call-code')
    expect(screen.queryByTestId('console')).toBeNull()                          // still waiting: the QR card
    const { act } = await import('@testing-library/react')
    act(() => { Sock.last!.push({ type: 'call', state: 'joined' }) })
    expect(screen.getByTestId('call-status')).toHaveTextContent(t.call.speakerJoined)
    act(() => { Sock.last!.push({ type: 'ready' }) })
    expect(screen.getByTestId('console')).toBeInTheDocument()
    expect(screen.getByTestId('phone')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: t.call.title })).toBeNull()    // the form is gone; the console has the width
    expect(screen.queryByTestId('call-code')).toBeNull()
    act(() => { Sock.last!.push({ type: 'analysis', level: 'high', score: 8, summary: '', seconds: 9, hits: [AUTH, OTP], tracks: [{ code: 'en-IN', text: TEXT, hits: [AUTH, OTP] }] }) })
    act(() => { Sock.last!.push({ type: 'alert', level: 'high' }) })
    expect(screen.getByTestId('phone-takeover')).toBeInTheDocument()
    expect(screen.getAllByTestId('graph-point')).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: /./ }).some((b) => b.textContent === t.call.end)).toBe(true)
  })
})
