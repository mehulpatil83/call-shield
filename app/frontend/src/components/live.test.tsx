import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import LivePanel from './LivePanel'
import LiveView from './LiveView'
import { STRINGS } from '../i18n'
import { initialLive, type LiveState } from '../live/state'

const hit = { category: 'otp_request', kind: 'request' as const, quote: 'share the otp', start: 7, end: 20, explanation: 'x', source: '' }
const live: LiveState = {
  ...initialLive, status: 'live', level: 'high', score: 8, seconds: 12, alert: 'high', hits: [hit],
  tracks: [{ code: 'en-IN', text: 'please share the otp now', hits: [hit] }],
}

describe('LiveView', () => {
  it('shows the meter, alert, evidence and highlighted transcript', () => {
    render(<LiveView t={STRINGS.en} state={live} onOpenReport={() => {}} onAgain={() => {}} />)
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '8')
    expect(screen.getByTestId('live-alert')).toHaveTextContent(STRINGS.en.live.alertHigh)
    expect(screen.getByTestId('live-level')).toHaveTextContent(STRINGS.en.levels.high)
    expect(screen.getByText(STRINGS.en.categories.otp_request.label)).toBeInTheDocument()
    expect(document.querySelector('mark.request')?.textContent).toBe('share the otp')
  })
  it('speaks Marathi', () => {
    render(<LiveView t={STRINGS.mr} state={live} onOpenReport={() => {}} onAgain={() => {}} />)
    expect(screen.getByTestId('live-alert')).toHaveTextContent(STRINGS.mr.live.alertHigh)
  })
  it('waits for speech, and offers the report at the end', async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    const { rerender } = render(<LiveView t={STRINGS.en} state={{ ...initialLive, status: 'live' }} onOpenReport={onOpen} onAgain={() => {}} />)
    expect(screen.getByText(STRINGS.en.live.waiting)).toBeInTheDocument()
    expect(screen.getByTestId('live-status')).toHaveTextContent(STRINGS.en.live.listening)
    rerender(<LiveView t={STRINGS.en} state={{ ...live, status: 'ended', id: 'abcdef012345' }} onOpenReport={onOpen} onAgain={() => {}} />)
    await user.click(screen.getByRole('button', { name: STRINGS.en.live.openReport }))
    expect(onOpen).toHaveBeenCalledWith('abcdef012345')
  })
  it('explains a too-short call and a reached time limit', () => {
    const { rerender } = render(<LiveView t={STRINGS.en} state={{ ...initialLive, status: 'ended', id: null }} onOpenReport={() => {}} onAgain={() => {}} />)
    expect(screen.getByText(STRINGS.en.live.tooShort)).toBeInTheDocument()
    rerender(<LiveView t={STRINGS.en} state={{ ...live, warning: 'limit:600' }} onOpenReport={() => {}} onAgain={() => {}} />)
    expect(screen.getByText(STRINGS.en.live.limitReached(600))).toBeInTheDocument()
  })
})

class FakeSocket {
  static last: FakeSocket | null = null
  binaryType = 'blob'
  readyState = 1
  sent: unknown[] = []
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  constructor(public url: string) { FakeSocket.last = this }
  send(d: unknown) { this.sent.push(d) }
  close() { this.readyState = 3 }
}

describe('LivePanel', () => {
  it('keeps the buttons disabled until consent is given, then connects with the chosen language', async () => {
    const user = userEvent.setup()
    render(<LivePanel t={STRINGS.en} onOpenReport={() => {}} createSocket={(u) => new FakeSocket(u) as unknown as WebSocket} />)
    const start = screen.getByRole('button', { name: STRINGS.en.live.startMic })
    expect(start).toBeDisabled()
    await user.selectOptions(screen.getByRole('combobox'), 'mr')
    await user.click(screen.getByRole('checkbox', { name: new RegExp(STRINGS.en.consent.slice(0, 20)) }))
    expect(start).toBeEnabled()
    await user.click(start)
    expect(FakeSocket.last!.url).toContain('/api/live?language=mr&consent=true')
    expect(screen.getByTestId('live-status')).toHaveTextContent(STRINGS.en.live.connecting)
  })
  it('shows the problem when the microphone is not available', async () => {
    const user = userEvent.setup()
    render(<LivePanel t={STRINGS.en} onOpenReport={() => {}} createSocket={(u) => new FakeSocket(u) as unknown as WebSocket} />)
    await user.click(screen.getByRole('checkbox', { name: new RegExp(STRINGS.en.consent.slice(0, 20)) }))
    await user.click(screen.getByRole('button', { name: STRINGS.en.live.startMic }))
    await act(async () => { await FakeSocket.last!.onmessage!({ data: JSON.stringify({ type: 'ready' }) }) })
    expect(await screen.findByTestId('live-error')).toBeInTheDocument()   // jsdom has no microphone
  })
  it('updates the meter from server messages', async () => {
    const user = userEvent.setup()
    render(<LivePanel t={STRINGS.en} onOpenReport={() => {}} createSocket={(u) => new FakeSocket(u) as unknown as WebSocket} />)
    await user.click(screen.getByRole('checkbox', { name: new RegExp(STRINGS.en.consent.slice(0, 20)) }))
    await user.click(screen.getByRole('button', { name: STRINGS.en.live.startMic }))
    const send = (m: object) => act(async () => { await FakeSocket.last!.onmessage!({ data: JSON.stringify(m) }) })
    await send({ type: 'analysis', level: 'elevated', score: 4.5, summary: '', seconds: 8, tracks: [], hits: [] })
    await send({ type: 'alert', level: 'elevated' })
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '4.5')
    expect(screen.getByTestId('live-alert')).toHaveTextContent(STRINGS.en.live.alertElevated)
  })
})
