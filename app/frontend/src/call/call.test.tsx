import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { SpeakerApp } from '../App'
import CallReceiver from '../components/CallReceiver'
import SpeakerPage from '../components/SpeakerPage'
import { STRINGS } from '../i18n'
import { initialLive, reduceLive } from '../live/state'

class FakeSocket {
  static last: FakeSocket | null = null
  binaryType = 'blob'
  readyState = 1
  sent: unknown[] = []
  onmessage: ((e: { data: unknown }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  constructor(public url: string) { FakeSocket.last = this }
  send(d: unknown) { this.sent.push(d) }
  close() { this.readyState = 3 }
  push(msg: object) { act(() => { this.onmessage?.({ data: JSON.stringify(msg) }) }) }
}
const t = STRINGS.en
const sock = () => FakeSocket.last!
const create = (u: string) => new FakeSocket(u) as unknown as WebSocket

describe('call states', () => {
  it('moves waiting -> joined -> live and ignores late "call" messages once live', () => {
    let s = reduceLive(initialLive, { type: '_connecting' })
    s = reduceLive(s, { type: 'call', state: 'waiting' })
    expect(s.status).toBe('waiting')
    s = reduceLive(s, { type: 'call', state: 'joined' })
    expect(s.status).toBe('joined')
    s = reduceLive(s, { type: 'ready' })
    expect(s.status).toBe('live')
    expect(reduceLive(s, { type: 'call', state: 'waiting' }).status).toBe('live')
    expect(reduceLive(s, { type: '_stopping' }).status).toBe('stopping')
  })
})

describe('SpeakerPage (the phone)', () => {
  it('needs a 6-digit code and the consent tick before it can join', async () => {
    const user = userEvent.setup()
    render(<SpeakerPage t={t} deps={{ createSocket: create, mic: async () => () => {} }} />)
    const join = screen.getByRole('button', { name: t.call.join })
    expect(join).toBeDisabled()
    await user.type(screen.getByLabelText(t.call.codeInput), '12ab34')
    expect(screen.getByLabelText(t.call.codeInput)).toHaveValue('1234')          // letters are dropped
    expect(screen.getByText(t.call.codeInvalid)).toBeInTheDocument()
    await user.type(screen.getByLabelText(t.call.codeInput), '56')
    expect(join).toBeDisabled()                                                  // no consent yet
    await user.click(screen.getByRole('checkbox'))
    expect(join).toBeEnabled()
  })

  it('sends the consent message only after the server says joined, then streams the microphone and shows no analysis', async () => {
    const user = userEvent.setup()
    let onChunk: (b: ArrayBuffer) => void = () => {}
    const stop = vi.fn()
    const mic = vi.fn(async (cb: (b: ArrayBuffer) => void) => { onChunk = cb; return stop })
    render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic }} />)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: t.call.join }))
    expect(sock().url).toContain('/api/call/speak?code=123456')
    expect(sock().sent).toEqual([])                                              // nothing before "joined"
    sock().push({ type: 'joined', language: 'en' })
    expect(JSON.parse(sock().sent[0] as string)).toEqual({ type: 'hello', consent: true })
    expect(mic).not.toHaveBeenCalled()                                           // no microphone before "ready"
    sock().push({ type: 'ready' })
    await waitFor(() => expect(screen.getByTestId('speaker-status')).toHaveTextContent(t.call.connected))
    const chunk = new Uint8Array([1, 2, 3, 4]).buffer
    act(() => onChunk(chunk))
    expect(sock().sent[1]).toBe(chunk)
    // a stray analysis message must never be drawn on the phone
    sock().push({ type: 'analysis', level: 'high', score: 9, summary: '', seconds: 3, tracks: [], hits: [] })
    expect(screen.queryByRole('meter')).toBeNull()
    expect(screen.getByText(t.call.nothingShown)).toBeInTheDocument()
    // mute sends silence of the same size
    await user.click(screen.getByRole('button', { name: t.call.mute }))
    act(() => onChunk(chunk))
    expect(new Uint8Array(sock().sent[2] as ArrayBuffer)).toEqual(new Uint8Array(4))
    // end
    await user.click(screen.getByRole('button', { name: t.call.endCall }))
    expect(stop).toHaveBeenCalled()
    expect(JSON.parse(sock().sent[3] as string)).toEqual({ type: 'stop' })
    sock().push({ type: 'ended' })
    expect(screen.getByTestId('speaker-ended')).toHaveTextContent(t.call.ended)
  })

  it('explains a blocked microphone and a server refusal', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic: async () => { throw new Error('denied') } }} />)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: t.call.join }))
    sock().push({ type: 'joined' })
    sock().push({ type: 'ready' })
    await waitFor(() => expect(screen.getByTestId('speaker-error')).toHaveTextContent(t.call.micDenied))
    unmount()
    render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic: async () => () => {} }} />)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: t.call.join }))
    sock().push({ type: 'error', message: 'That code is not valid, or the call has expired.' })
    expect(screen.getByTestId('speaker-error')).toHaveTextContent('not valid')
  })

  it('treats a dropped connection as an error, not as a finished call', async () => {
    const user = userEvent.setup()
    render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic: async () => () => {} }} />)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: t.call.join }))
    act(() => sock().onclose?.())
    expect(screen.getByTestId('speaker-error')).toHaveTextContent(t.call.lostConnection)
  })
})

describe('SpeakerApp (what the phone gets on the tunnel address)', () => {
  it('shows only the Speaker screen: no upload, history or live-check tabs', () => {
    render(<SpeakerApp />)
    expect(screen.getByRole('heading', { name: t.call.speakerTitle })).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).toBeNull()
  })
})

const created = { code: '482913', language: 'en', public_url: 'https://x.trycloudflare.com', join_url: 'https://x.trycloudflare.com/#/join/482913', expires_in: 600 }
const hit = { category: 'otp_request', kind: 'request' as const, quote: 'share the otp', start: 7, end: 20, explanation: 'x', source: '' }

describe('CallReceiver (the laptop)', () => {
  const setup = (over: { listenPlayer?: { push: () => void; close: () => void } } = {}) => {
    const makeCall = vi.fn().mockResolvedValue(created)
    const onOpen = vi.fn()
    render(<CallReceiver t={t} onOpenReport={onOpen}
                         loadConfig={async () => ({ public_url: 'https://x.trycloudflare.com' })}
                         deps={{ createSocket: create, createCall: makeCall, createPlayer: () => over.listenPlayer ?? { push() {}, close() {} } }} />)
    return { makeCall, onOpen }
  }

  it('needs consent, then creates the call and shows the code and join address', async () => {
    const user = userEvent.setup()
    const { makeCall } = setup()
    const start = screen.getByRole('button', { name: t.call.start })
    expect(start).toBeDisabled()
    await waitFor(() => expect(screen.getByLabelText(new RegExp(t.call.publicLabel.slice(0, 14)))).toHaveValue('https://x.trycloudflare.com'))
    await user.click(screen.getByLabelText(t.call.consent))
    await user.click(start)
    expect(makeCall).toHaveBeenCalledWith('en', true, false, 'https://x.trycloudflare.com')
    await waitFor(() => expect(screen.getByTestId('call-code')).toHaveTextContent('482913'))
    expect(screen.getByTestId('call-join-url')).toHaveTextContent('/#/join/482913')
    await waitFor(() => expect(document.querySelector('img.qr')).not.toBeNull())
    expect(sock().url).toContain('/api/call/receive?code=482913')
  })

  it('walks through waiting, joined and live, showing the meter, alert, evidence and what to do now', async () => {
    const user = userEvent.setup()
    setup()
    await user.click(screen.getByLabelText(t.call.consent))
    await user.click(screen.getByRole('button', { name: t.call.start }))
    await waitFor(() => expect(sock()).toBeTruthy())
    sock().push({ type: 'call', state: 'waiting' })
    expect(screen.getByTestId('call-status')).toHaveTextContent(t.call.waitingSpeaker)
    sock().push({ type: 'call', state: 'joined' })
    expect(screen.getByTestId('call-status')).toHaveTextContent(t.call.speakerJoined)
    sock().push({ type: 'ready' })
    expect(screen.queryByTestId('call-code')).toBeNull()                         // the code is hidden once the call is live
    sock().push({ type: 'analysis', level: 'high', score: 8, summary: '', seconds: 9, hits: [hit],
                  tracks: [{ code: 'en-IN', text: 'please share the otp now', hits: [hit] }] })
    sock().push({ type: 'alert', level: 'high' })
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '8')
    expect(screen.getByTestId('live-alert')).toHaveTextContent(t.live.alertHigh)
    expect(document.querySelector('mark.request')?.textContent).toBe('share the otp')
    expect(screen.getByTestId('live-advice')).toHaveTextContent(t.advice.high[0])
  })

  it('has Listen off by default and sends the switch to the server', async () => {
    const user = userEvent.setup()
    const player = { push: vi.fn(), close: vi.fn() }
    setup({ listenPlayer: player })
    await user.click(screen.getByLabelText(t.call.consent))
    await user.click(screen.getByRole('button', { name: t.call.start }))
    await waitFor(() => expect(sock()).toBeTruthy())
    sock().push({ type: 'call', state: 'waiting' })
    sock().push({ type: 'ready' })
    const box = screen.getByLabelText(t.call.listen)
    expect(box).not.toBeChecked()
    await user.click(box)
    expect(JSON.parse(sock().sent.at(-1) as string)).toEqual({ type: 'listen', on: true })
    const pcm = new Int16Array([1, 2, 3]).buffer
    act(() => sock().onmessage?.({ data: pcm }))
    expect(player.push).toHaveBeenCalledWith(pcm)
    await user.click(box)
    expect(JSON.parse(sock().sent.at(-1) as string)).toEqual({ type: 'listen', on: false })
    expect(player.close).toHaveBeenCalled()
  })

  it('ends the call from the receiver and opens the stored report', async () => {
    const user = userEvent.setup()
    const { onOpen } = setup()
    await user.click(screen.getByLabelText(t.call.consent))
    await user.click(screen.getByRole('button', { name: t.call.start }))
    await waitFor(() => expect(sock()).toBeTruthy())
    sock().push({ type: 'ready' })
    await user.click(screen.getByRole('button', { name: t.call.end }))
    expect(JSON.parse(sock().sent.at(-1) as string)).toEqual({ type: 'end' })
    sock().push({ type: 'ended', id: 'abcdef012345', level: 'high' })
    await user.click(screen.getByRole('button', { name: t.live.openReport }))
    expect(onOpen).toHaveBeenCalledWith('abcdef012345')
  })

  it('shows a clear error when the call cannot be created', async () => {
    const user = userEvent.setup()
    render(<CallReceiver t={t} onOpenReport={() => {}} loadConfig={async () => ({ public_url: null })}
                         deps={{ createSocket: create, createCall: vi.fn().mockRejectedValue(new Error('Another live check is running.')) }} />)
    await user.click(screen.getByLabelText(t.call.consent))
    await user.click(screen.getByRole('button', { name: t.call.start }))
    await waitFor(() => expect(screen.getByTestId('call-error')).toHaveTextContent('Another live check'))
  })
})

describe('call translations', () => {
  it('have every text in every language', () => {
    const keys = Object.keys(STRINGS.en.call).sort()
    for (const lang of ['hi', 'mr'] as const) {
      expect(Object.keys(STRINGS[lang].call).sort()).toEqual(keys)
      for (const k of keys) {
        const v = (STRINGS[lang].call as unknown as Record<string, unknown>)[k]
        expect(typeof v === 'function' ? (v as (n: number) => string)(10) : (v as string).trim(), `${lang}:${k}`).not.toBe('')
      }
      expect(STRINGS[lang].call.expires(10)).toContain('10')
    }
  })
})
