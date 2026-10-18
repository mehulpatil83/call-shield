import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import CallReceiver from '../components/CallReceiver'
import SpeakerPage from '../components/SpeakerPage'
import { STRINGS } from '../i18n'
import { initialLive, reduceLive } from '../live/state'
import { rmsOfPcm16 } from '../live/pcm'
import { AUDIO_QUIET_MS, AUDIO_STALE_MS, audioStatus } from './useCallReceiver'
import { GRACE_MS, RETRY_MS, SILENCE_MS } from './useSpeaker'

const t = STRINGS.en

class FakeSocket {
  static all: FakeSocket[] = []
  binaryType = 'blob'
  readyState = 1
  sent: unknown[] = []
  onmessage: ((e: { data: unknown }) => unknown) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  constructor(public url: string) { FakeSocket.all.push(this) }
  send(d: unknown) { this.sent.push(d) }
  close() { this.readyState = 3 }
  async push(msg: object) { await act(async () => { await this.onmessage?.({ data: JSON.stringify(msg) }) }) }
  drop() { this.readyState = 3; act(() => { this.onclose?.() }) }
}
const last = () => FakeSocket.all[FakeSocket.all.length - 1]
const create = (u: string) => new FakeSocket(u) as unknown as WebSocket
const loud = (amp: number) => new Int16Array(512).fill(Math.round(amp * 32767)).buffer
const tick = async (ms: number) => { await act(async () => { await vi.advanceTimersByTimeAsync(ms) }) }

function fakeMic() {
  const stops: ReturnType<typeof vi.fn>[] = []
  let onChunk: (b: ArrayBuffer) => void = () => {}
  const mic = vi.fn(async (cb: (b: ArrayBuffer) => void) => { onChunk = cb; const stop = vi.fn(); stops.push(stop); return stop })
  return { mic, stops, chunk: (amp: number) => act(() => onChunk(loud(amp))) }
}

beforeEach(() => { FakeSocket.all = []; sessionStorage.clear(); vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers(); sessionStorage.clear() })

/** Render the phone page, join, and walk it to the live state. */
async function goLive(mic = fakeMic(), token = 'tok-123') {
  render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic: mic.mic }} />)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: t.call.join }))
  await last().push({ type: 'joined' })
  await last().push({ type: 'ready', resume: token })
  return mic
}

describe('microphone level bar and silence warning', () => {
  it('shows how loud the microphone is', async () => {
    const m = await goLive()
    expect(screen.getByTestId('speaker-level')).toHaveAttribute('aria-valuenow', '0')
    await tick(150)
    m.chunk(0.1)
    expect(Number(screen.getByTestId('speaker-level').getAttribute('aria-valuenow'))).toBeGreaterThan(30)
    expect(screen.getByText(t.call.speakHint)).toBeInTheDocument()
  })

  it('warns after a few seconds of silence and clears the warning when speech comes back', async () => {
    const m = await goLive()
    await tick(SILENCE_MS - 1000)
    expect(screen.queryByTestId('speaker-silence')).toBeNull()
    await tick(2500)
    expect(screen.getByTestId('speaker-silence')).toHaveTextContent(t.call.silenceWarning)
    m.chunk(0.1)
    await tick(1100)
    expect(screen.queryByTestId('speaker-silence')).toBeNull()
  })

  it('does not warn about silence while muted', async () => {
    await goLive()
    await tick(SILENCE_MS + 2500)
    expect(screen.getByTestId('speaker-silence')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: t.call.mute }))
    expect(screen.queryByTestId('speaker-silence')).toBeNull()
    await tick(SILENCE_MS + 2500)
    expect(screen.queryByTestId('speaker-silence')).toBeNull()
    expect(screen.getByText(t.call.muted)).toBeInTheDocument()
  })
})

describe('automatic rejoin', () => {
  it('rejoins the same call with its resume token after a dropped connection and restarts the microphone', async () => {
    const m = await goLive()
    const first = last()
    expect(m.mic).toHaveBeenCalledTimes(1)
    first.drop()
    expect(screen.getByTestId('speaker-status')).toHaveTextContent(t.call.reconnecting)
    expect(m.stops[0]).toHaveBeenCalled()                                      // no microphone running while disconnected
    expect(FakeSocket.all).toHaveLength(1)
    await tick(RETRY_MS + 50)
    expect(FakeSocket.all).toHaveLength(2)
    expect(last().url).toContain('/api/call/speak?code=123456&resume=tok-123')
    await last().push({ type: 'ready', resume: 'tok-123', resumed: true })
    expect(screen.getByTestId('speaker-status')).toHaveTextContent(t.call.connected)
    expect(m.mic).toHaveBeenCalledTimes(2)
    expect(first.sent.filter((x) => typeof x === 'string').length).toBe(1)    // only the consent message went to the old socket
    // audio now goes to the new socket
    m.chunk(0.1)
    expect(last().sent.some((x) => x instanceof ArrayBuffer)).toBe(true)
  })

  it('keeps retrying while the server is unreachable, then gives up after the grace period', async () => {
    await goLive()
    last().drop()
    for (let i = 0; i < 5; i++) { await tick(RETRY_MS + 50); last().drop() }
    expect(FakeSocket.all.length).toBeGreaterThan(4)
    await tick(GRACE_MS)
    last().drop()
    await tick(RETRY_MS + 50)
    expect(screen.getByTestId('speaker-error')).toHaveTextContent(t.call.lostConnection)
    const count = FakeSocket.all.length
    await tick(10_000)
    expect(FakeSocket.all).toHaveLength(count)                                   // it stopped trying
    expect(sessionStorage.getItem('cs-call')).toBeNull()
  })

  it('stops trying when the server says the call can no longer be rejoined', async () => {
    await goLive()
    last().drop()
    await tick(RETRY_MS + 50)
    await last().push({ type: 'error', message: 'This call can no longer be rejoined.' })
    expect(screen.getByTestId('speaker-error')).toHaveTextContent('no longer be rejoined')
    const count = FakeSocket.all.length
    last().drop()
    await tick(5000)
    expect(FakeSocket.all).toHaveLength(count)
  })

  it('a call that never got started is not retried', async () => {
    render(<SpeakerPage t={t} initialCode="123456" deps={{ createSocket: create, mic: fakeMic().mic }} />)
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: t.call.join }))
    last().drop()
    expect(screen.getByTestId('speaker-error')).toHaveTextContent(t.call.lostConnection)
    await tick(5000)
    expect(FakeSocket.all).toHaveLength(1)
  })

  it('offers to rejoin after the page was reloaded, within the grace period only', async () => {
    sessionStorage.setItem('cs-call', JSON.stringify({ code: '654321', token: 'saved-token', at: Date.now() - 10_000 }))
    const m = fakeMic()
    render(<SpeakerPage t={t} deps={{ createSocket: create, mic: m.mic }} />)
    expect(screen.getByTestId('speaker-rejoin')).toBeInTheDocument()
    expect(FakeSocket.all).toHaveLength(0)                                       // needs a tap first
    fireEvent.click(screen.getByRole('button', { name: t.call.rejoinButton }))
    expect(last().url).toContain('code=654321&resume=saved-token')
    await last().push({ type: 'ready', resume: 'saved-token', resumed: true })
    expect(screen.getByTestId('speaker-status')).toHaveTextContent(t.call.connected)
    expect(m.mic).toHaveBeenCalledTimes(1)
  })

  it('does not offer a call that is too old, and ending the call forgets it', async () => {
    sessionStorage.setItem('cs-call', JSON.stringify({ code: '654321', token: 'old', at: Date.now() - GRACE_MS - 5000 }))
    const { unmount } = render(<SpeakerPage t={t} deps={{ createSocket: create, mic: fakeMic().mic }} />)
    expect(screen.queryByTestId('speaker-rejoin')).toBeNull()
    unmount()
    await goLive()
    expect(sessionStorage.getItem('cs-call')).not.toBeNull()
    fireEvent.click(screen.getByRole('button', { name: t.call.endCall }))
    expect(sessionStorage.getItem('cs-call')).toBeNull()
  })
})

describe('Receiver: audio indicator and reconnecting banner', () => {
  const created = { code: '482913', language: 'en', public_url: 'https://x.trycloudflare.com', join_url: 'https://x.trycloudflare.com/#/join/482913', expires_in: 600 }
  async function live() {
    render(<CallReceiver t={t} onOpenReport={() => {}} loadConfig={async () => ({ public_url: null })}
                         deps={{ createSocket: create, createCall: vi.fn().mockResolvedValue(created) }} />)
    fireEvent.click(screen.getByLabelText(t.call.consent))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: t.call.start })); await vi.advanceTimersByTimeAsync(10) })
    await last().push({ type: 'call', state: 'waiting' })
    await last().push({ type: 'ready' })
  }

  it('says audio is arriving, and how loud', async () => {
    await live()
    expect(screen.getByTestId('call-audio')).toHaveAttribute('data-state', 'none')
    await last().push({ type: 'audio', rms: 0.1 })
    expect(screen.getByTestId('call-audio')).toHaveAttribute('data-state', 'ok')
    expect(screen.getByText(t.call.receivingAudio)).toBeInTheDocument()
    expect(Number(screen.getByRole('meter', { name: t.call.audioLevelLabel }).getAttribute('aria-valuenow'))).toBeGreaterThan(30)
  })

  it('warns when audio stops arriving and when only silence arrives', async () => {
    await live()
    await last().push({ type: 'audio', rms: 0.1 })
    await tick(AUDIO_STALE_MS + 1500)
    expect(screen.getByTestId('call-audio')).toHaveAttribute('data-state', 'none')
    expect(screen.getByText(t.call.audioNone)).toBeInTheDocument()
    for (let i = 0; i < 8; i++) { await last().push({ type: 'audio', rms: 0 }); await tick(1000) }
    expect(screen.getByTestId('call-audio')).toHaveAttribute('data-state', 'silent')
    expect(screen.getByText(t.call.audioSilent)).toBeInTheDocument()
    await last().push({ type: 'audio', rms: 0.1 })
    expect(screen.getByTestId('call-audio')).toHaveAttribute('data-state', 'ok')
  })

  it('shows a banner while the phone is reconnecting and returns to normal when it is back', async () => {
    await live()
    await last().push({ type: 'call', state: 'reconnecting', seconds: 60 })
    expect(screen.getByTestId('call-reconnecting')).toHaveTextContent('Waiting up to 60 seconds')
    expect(screen.queryByTestId('call-audio')).toBeNull()
    await last().push({ type: 'call', state: 'live' })
    expect(screen.queryByTestId('call-reconnecting')).toBeNull()
    expect(screen.getByTestId('call-audio')).toBeInTheDocument()
  })
})

describe('pure helpers', () => {
  it('audioStatus', () => {
    expect(audioStatus(10_000, 0, 0)).toBe('none')
    expect(audioStatus(10_000, 9_000, 9_000)).toBe('ok')
    expect(audioStatus(20_000, 15_000, 15_000)).toBe('none')                       // stale
    expect(audioStatus(20_000, 19_000, 19_000 - AUDIO_QUIET_MS - 1)).toBe('silent')
  })

  it('rmsOfPcm16', () => {
    expect(rmsOfPcm16(new ArrayBuffer(0))).toBe(0)
    expect(rmsOfPcm16(new Int16Array(100).buffer)).toBe(0)
    expect(rmsOfPcm16(loud(0.5))).toBeCloseTo(0.5, 2)
    expect(rmsOfPcm16(new Uint8Array([1, 2, 3]).buffer)).toBeGreaterThanOrEqual(0)    // odd length does not throw
  })

  it('live -> reconnecting -> live, and the call can still end while reconnecting', () => {
    let s = reduceLive(initialLive, { type: '_connecting' })
    s = reduceLive(s, { type: 'ready' })
    s = reduceLive(s, { type: 'call', state: 'reconnecting', seconds: 60 })
    expect(s.status).toBe('reconnecting')
    expect(reduceLive(s, { type: 'call', state: 'waiting' }).status).toBe('reconnecting')
    expect(reduceLive(s, { type: '_stopping' }).status).toBe('stopping')
    expect(reduceLive(s, { type: 'call', state: 'live' }).status).toBe('live')
    expect(reduceLive(s, { type: 'ended', id: 'abc', level: 'low', max_level: 'low' } as never).status).toBe('ended')
    expect(reduceLive(initialLive, { type: 'call', state: 'reconnecting' }).status).toBe('idle')   // only a live call can reconnect
  })
})
