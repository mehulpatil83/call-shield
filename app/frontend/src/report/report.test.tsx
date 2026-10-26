import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { STRINGS } from '../i18n'
import { currentIndex, describe as describeEvent, filterEvents, fmtCall, fmtClock, markQuotes, stats } from './derive'
import ReportPage from './ReportPage'
import { RTEXT } from './strings'
import { SOURCES, type AiResult, type Session, type SessionResponse } from './types'

vi.mock('../api', async (orig) => ({ ...(await orig<typeof import('../api')>()), deleteAnalysis: vi.fn(async () => ({ deleted: 'x' })) }))

const W = (s: string) => `2026-10-24T10:00:${s}.000`
const SESSION: Session = {
  version: 1, id: 'aaaaaaaaaaaa', started_at: W('00'), language: 'en', duration: 40, max_level: 'high', level: 'high', digits_masked: true, timestamps_note: 'x',
  segments: [
    { track: 'en-IN', first_t: 3, last_t: 3, first_wall: W('03'), text: 'this is your bank please read the otp ••• now' },
    { track: 'en-IN', first_t: 12, last_t: 12, first_wall: W('12'), text: 'otherwise the account will be blocked today' },
  ],
  events: [
    { i: 0, t: 0, wall: W('00'), source: 'system', kind: 'call_started' },
    { i: 1, t: 3.1, wall: W('03'), source: 'system', kind: 'first_words', track: 'en-IN' },
    { i: 2, t: 3.2, wall: W('03'), source: 'rules', kind: 'tactic', category: 'otp_request', kind_of: 'request', quote: 'read the otp', track: 'en-IN' },
    { i: 3, t: 3.2, wall: W('03'), source: 'rules', kind: 'level', frm: 'low', to: 'elevated', score: 3 },
    { i: 4, t: 3.2, wall: W('03'), source: 'alert', kind: 'alert', level: 'elevated' },
    { i: 5, t: 12.4, wall: W('12'), source: 'rules', kind: 'tactic', category: 'threat', kind_of: 'pressure', quote: 'will be blocked', track: 'en-IN' },
    { i: 6, t: 12.4, wall: W('12'), source: 'rules', kind: 'level', frm: 'elevated', to: 'high', score: 6 },
    { i: 7, t: 12.4, wall: W('12'), source: 'alert', kind: 'alert', level: 'high' },
    { i: 8, t: 20, wall: W('20'), source: 'connection', kind: 'phone_dropped' },
    { i: 9, t: 40, wall: W('40'), source: 'voice', kind: 'voice_check', label: 'Inconclusive', status: 'inconclusive' },
  ],
  risk: [{ t: 0, level: 'low', score: 0, model: null }, { t: 3.2, level: 'elevated', score: 3, model: null }, { t: 12.4, level: 'high', score: 6, model: 0.9 }],
}
const AI: AiResult = { lang: 'en', model: '@cf/test', provider: 'cloudflare', made_at: 'x', summary: 'The caller asked for a code.', dropped_quotes: 0,
  what_happened: [{ at: 12.4, text: 'Threat made.' }], why_risky: ['A code was requested.'], advice: ['Hang up.'], quotes: ['read the otp'] }
const resp = (over: Partial<SessionResponse> = {}): SessionResponse => ({ session: SESSION, ai: {}, ai_status: { configured: false, provider: null, model: null, sends_to: null }, ...over })

function page(over: Partial<SessionResponse> = {}, extra: Partial<React.ComponentProps<typeof ReportPage>> = {}) {
  const props = { id: 'aaaaaaaaaaaa', lang: 'en' as const, onBack: vi.fn(), onTechnical: vi.fn(), onDeleted: vi.fn(), load: async () => resp(over), ...extra }
  return { props, ...render(<ReportPage {...props} />) }
}
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

describe('report helpers', () => {
  it('formats call time and clock time', () => {
    expect(fmtCall(0)).toBe('00:00.0'); expect(fmtCall(65.34)).toBe('01:05.3'); expect(fmtCall(-4)).toBe('00:00.0')
    expect(fmtClock('2026-10-24T10:03:09.123')).toBe('10:03:09')
  })
  it('derives the headline numbers', () => {
    const s = stats(SESSION)
    expect(s.firstAlertAt).toBe(3.2); expect(s.highAt).toBe(12.4); expect(s.tactics).toEqual(['otp_request', 'threat']); expect(s.modelPeak).toBe(0.9)
    expect(s.voice).toBe('Inconclusive')
  })
  it('finds the current event and marks quotes ignoring case', () => {
    expect(currentIndex(SESSION.events, null)).toBe(-1); expect(currentIndex(SESSION.events, 3.2)).toBe(4); expect(currentIndex(SESSION.events, 100)).toBe(9)
    expect(markQuotes('Please READ the OTP now', ['read the otp']).map((p) => [p.text, p.hit])).toEqual([['Please ', false], ['READ the OTP', true], [' now', false]])
    expect(markQuotes('nothing', ['zzz'])).toEqual([{ text: 'nothing', hit: false }])
  })
  it('filters events by source, tactic and search words', () => {
    const base = { sources: new Set(SOURCES), category: null, query: '' }
    const r = RTEXT.en, t = STRINGS.en
    expect(filterEvents(SESSION.events, base, r, t)).toHaveLength(10)
    expect(filterEvents(SESSION.events, { ...base, sources: new Set(['alert'] as const) }, r, t).map((e) => e.i)).toEqual([4, 7])
    expect(filterEvents(SESSION.events, { ...base, category: 'threat' }, r, t).map((e) => e.i)).toEqual([5])
    expect(filterEvents(SESSION.events, { ...base, query: 'BLOCKED' }, r, t).map((e) => e.i)).toEqual([5])
    expect(describeEvent(SESSION.events[3], r, t).text).toBe('Risk changed from low to elevated (Rules)')
    expect(describeEvent(SESSION.events[4], r, t).text).toBe('Alert shown: elevated')
  })
  it('has every report string in English, Hindi and Marathi', () => {
    const keys = (o: unknown, p = ''): string[] => (o && typeof o === 'object' ? Object.entries(o).flatMap(([k, v]) => keys(v, `${p}${k}.`)) : [p])
    expect(keys(RTEXT.hi)).toEqual(keys(RTEXT.en)); expect(keys(RTEXT.mr)).toEqual(keys(RTEXT.en))
    for (const l of ['en', 'hi', 'mr'] as const) {
      expect(RTEXT[l].quick({ duration: '00:40.0', level: 'High', firstAlert: '00:03.2', tactics: ['a'] }).length).toBeGreaterThan(10)
      expect(RTEXT[l].ev.level('A', 'B', 'C')).toContain('B')
    }
  })
})

describe('ReportPage', () => {
  it('shows the verdict, the key times and a quick summary', async () => {
    page()
    expect(await screen.findByTestId('rp-verdict')).toHaveTextContent(STRINGS.en.levels.high)
    expect(screen.getByTestId('rp-first-alert')).toHaveTextContent('00:03.2')
    expect(screen.getByTestId('rp-high-at')).toHaveTextContent('00:12.4')
    expect(screen.getByTestId('rp-quick').textContent).toContain('first alert came at 00:03.2')
  })

  it('lists every event with call time AND clock time, in order, and highlights the quoted words', async () => {
    page()
    const list = await screen.findByTestId('rp-events')
    const rows = within(list).getAllByRole('listitem')
    expect(rows).toHaveLength(10)
    expect(rows[2].textContent).toContain('00:03.2'); expect(rows[2].textContent).toContain('10:00:03'); expect(rows[2].textContent).toContain('read the otp')
    const marks = within(screen.getByTestId('rp-transcript')).getAllByText(/read the otp|will be blocked/)
    expect(marks.every((m) => m.tagName === 'MARK')).toBe(true)
  })

  it('clicking an event moves the cursor, dims what comes later, and the arrow keys move it too', async () => {
    page()
    const list = await screen.findByTestId('rp-events')
    fireEvent.click(within(list).getAllByRole('button')[5])               // the threat at 12.4 s
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:12.4')
    const rows = within(list).getAllByRole('listitem')
    expect(rows[7].getAttribute('aria-current')).toBe('true')                         // the last event at or before 12.4 s
    expect(rows[8].className).toContain('future'); expect(rows[9].className).toContain('future'); expect(rows[3].className).not.toContain('future')
    const chart = screen.getByTestId('rp-chart')
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:13.4')
    fireEvent.keyDown(chart, { key: 'Home' })
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:00.0')
    fireEvent.click(screen.getByRole('button', { name: RTEXT.en.showAll }))
    expect(screen.queryByTestId('rp-cursor')).toBeNull()
  })

  it('filters by source and by search words', async () => {
    page()
    const list = await screen.findByTestId('rp-events')
    fireEvent.click(screen.getByRole('button', { name: RTEXT.en.sources.rules }))
    expect(within(list).getAllByRole('listitem')).toHaveLength(6)
    fireEvent.change(screen.getByLabelText(RTEXT.en.searchLabel), { target: { value: 'blocked' } })
    expect(screen.getByText(RTEXT.en.noEvents)).toBeTruthy()           // the only match was a rules event, which is switched off
    expect(within(screen.getByTestId('rp-transcript')).getAllByRole('paragraph')).toHaveLength(1)
  })

  it('replays the call: the cursor advances by itself and stops at the end', async () => {
    vi.useFakeTimers()
    page()
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    fireEvent.click(screen.getByTestId('rp-play'))
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:02.0')                 // 2x speed for one second
    await act(async () => { await vi.advanceTimersByTimeAsync(30000) })
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:40.0')
    expect(screen.getByTestId('rp-play')).toHaveTextContent(RTEXT.en.replay)
  })

  it('shows the page in the language it is given', async () => {
    const { props, rerender } = page()
    await screen.findByTestId('rp-verdict')
    expect(screen.getByText(RTEXT.en.timelineTitle)).toBeTruthy()
    rerender(<ReportPage {...props} lang="mr" />)
    expect(screen.getByText(RTEXT.mr.timelineTitle)).toBeTruthy()
    expect(screen.queryByLabelText(RTEXT.en.language)).toBeNull()                       // the language is chosen once, in the page header
  })

  it('combines what the rules, the language model and the AI summary found', async () => {
    page({ ai: { en: AI }, ai_status: { configured: true, provider: 'groq', model: 'm', sends_to: 'Groq' } })
    const box = await screen.findByTestId('rp-combined')
    expect(within(box).getByTestId('rp-decided')).toHaveTextContent(RTEXT.en.combined.decidedRules)
    expect(within(within(box).getByTestId('cmb-rules')).getByText(STRINGS.en.levels.high)).toBeTruthy()
    expect(within(box).getByTestId('cmb-rules').textContent).toContain(RTEXT.en.combined.tactics(2))
    expect(within(box).getByTestId('cmb-model').textContent).toContain('90%')                       // the model's peak from the risk history
    expect(within(box).getByTestId('cmb-model').textContent).toContain(RTEXT.en.combined.modelAgrees)
    expect(within(box).getByTestId('cmb-ai').textContent).toContain('The caller asked for a code.')
  })

  it('says when the language model is what raised the alert', async () => {
    const raised = { ...SESSION, events: SESSION.events.map((e) => (e.i === 6 ? { ...e, source: 'model' as const } : e)) }
    page({ session: raised })
    const box = await screen.findByTestId('rp-combined')
    expect(within(box).getByTestId('rp-decided')).toHaveTextContent(RTEXT.en.combined.decidedModel('00:12.4'))
    expect(within(box).getByTestId('cmb-model').textContent).toContain(RTEXT.en.combined.modelRaised('00:12.4'))
  })

  it('without an AI service it says so and offers no button', async () => {
    page()
    const card = await screen.findByTestId('rp-ai')
    expect(within(card).getByText(RTEXT.en.ai.notSet)).toBeTruthy()
    expect(within(card).queryByRole('button')).toBeNull()
  })

  it('asks for consent before text is sent, then shows the AI summary in the chosen language', async () => {
    const writeAi = vi.fn(async () => ({ ai: AI, cached: false }))
    page({ ai_status: { configured: true, provider: 'cloudflare', model: '@cf/test', sends_to: 'Cloudflare Workers AI' } }, { writeAi })
    const card = await screen.findByTestId('rp-ai')
    const button = within(card).getByRole('button', { name: RTEXT.en.ai.write })
    expect(button).toBeDisabled()
    expect(card.textContent).toContain('Cloudflare Workers AI')
    fireEvent.click(within(card).getByRole('checkbox', { name: RTEXT.en.ai.consent('Cloudflare Workers AI') }))
    fireEvent.click(button)
    await waitFor(() => expect(screen.getByTestId('rp-ai-text')).toBeTruthy())
    expect(writeAi).toHaveBeenCalledWith('aaaaaaaaaaaa', 'en', true, false)
    expect(screen.getByTestId('rp-ai-text').textContent).toContain('The caller asked for a code.')
    expect(screen.getByTestId('rp-ai-text').textContent).toContain(RTEXT.en.ai.warn)
    fireEvent.click(within(screen.getByTestId('rp-ai-text')).getByRole('button', { name: /read the otp/ }))
    expect(screen.getByTestId('rp-cursor')).toHaveTextContent('00:03.0')                 // a quote jumps to where it was said
  })

  it('shows a stored AI summary for the chosen language without asking again, and shows errors', async () => {
    const writeAi = vi.fn(async () => { throw new Error('The free daily allowance of the AI service may be used up.') })
    page({ ai: { en: AI }, ai_status: { configured: true, provider: 'cloudflare', model: 'm', sends_to: 'x' } }, { writeAi })
    expect((await screen.findByTestId('rp-ai-text')).textContent).toContain('Threat made.')
    expect(writeAi).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: RTEXT.en.ai.again }))
    expect(await screen.findByRole('alert')).toHaveTextContent('allowance')
  })

  it('tells which models were tried when the first choice was not available', async () => {
    const ai = { ...AI, attempts: [{ model: 'a:free', result: 'not available' }, { model: 'b:free', result: 'rate limited' }, { model: 'c:free', result: 'ok' }] }
    page({ ai: { en: ai }, ai_status: { configured: true, provider: 'openrouter', model: 'auto (free models)', sends_to: 'OpenRouter' } })
    expect((await screen.findByTestId('rp-ai-text')).textContent).toContain(RTEXT.en.ai.fellBack(2))
    expect(RTEXT.en.ai.fellBack(1)).toContain('1 other free model was')
  })

  it('deletes after confirmation and reports a missing timeline', async () => {
    const { props } = page()
    await screen.findByTestId('rp-verdict')
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: RTEXT.en.delete }))
    await waitFor(() => expect(props.onDeleted).toHaveBeenCalled())
    render(<ReportPage id="bbbbbbbbbbbb" lang="en" onBack={() => {}} onTechnical={() => {}} onDeleted={() => {}}
                       load={async () => { throw new Error('There is no timeline') }} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('There is no timeline')
  })
})
