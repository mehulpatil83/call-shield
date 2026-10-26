import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AppBackdrop from './Backdrop'
import { EffectsProvider, useAtmosphere, useFps, useFpsWatchdog } from './effects'
import EffectsControl from './EffectsControl'
import GlitchLayer from './GlitchLayer'
import HoloCard from './HoloCard'
import PhoneFrame from './PhoneFrame'
import { PHONE_RATIO, SCREEN, phoneBezel } from './phoneBezel'
import { FXTEXT } from './text'
import { GLITCH, PALETTES, PHONE_LOOK } from './atmosphere'

afterEach(() => { localStorage.clear(); vi.useRealTimers(); vi.unstubAllGlobals() })

function Mode() { return <span data-testid="mode">{useFps().mode}</span> }
function Atmosphere({ level }: { level: 'low' | 'elevated' | 'high' }) { useAtmosphere(level); return null }

describe('effects settings', () => {
  it('start at full, remember the choice, and Off removes the background', () => {
    const { unmount } = render(<EffectsProvider><AppBackdrop /><EffectsControl lang="en" /><Mode /></EffectsProvider>)
    expect(screen.getByTestId('mode')).toHaveTextContent('full'); expect(screen.getByTestId('fx-backdrop')).toBeTruthy()
    fireEvent.change(screen.getByLabelText(FXTEXT.en.label), { target: { value: 'off' } })
    expect(screen.queryByTestId('fx-backdrop')).toBeNull(); expect(localStorage.getItem('cs-fx')).toBe('off')
    unmount()
    render(<EffectsProvider><Mode /></EffectsProvider>)
    expect(screen.getByTestId('mode')).toHaveTextContent('off')                               // remembered
  })

  it('the background follows the risk level of the page and calms down when the page goes away', () => {
    const { rerender } = render(<EffectsProvider><AppBackdrop /><Atmosphere level="elevated" /></EffectsProvider>)
    expect(screen.getByTestId('fx-backdrop')).toHaveAttribute('data-level', 'elevated')
    rerender(<EffectsProvider><AppBackdrop /><Atmosphere level="high" /></EffectsProvider>)
    expect(screen.getByTestId('fx-backdrop')).toHaveAttribute('data-level', 'high')
    rerender(<EffectsProvider><AppBackdrop /></EffectsProvider>)
    expect(screen.getByTestId('fx-backdrop')).toHaveAttribute('data-level', 'low')
  })

  it('the reduced mode is quiet and every level has a palette, a glitch tone and a phone look', () => {
    localStorage.setItem('cs-fx', 'reduced')
    render(<EffectsProvider><AppBackdrop /></EffectsProvider>)
    expect(screen.getByTestId('fx-backdrop')).toHaveAttribute('data-mode', 'reduced')
    for (const l of ['low', 'elevated', 'high'] as const) {
      expect(PALETTES[l].colors.length).toBeGreaterThanOrEqual(2); expect(PHONE_LOOK[l].preset).toBeTruthy(); expect(GLITCH[l].dark.colors.length).toBeGreaterThan(0)
    }
    expect(GLITCH.alert.dark.base).toBeTruthy()
  })

  it('lowers itself when the screen is too slow, tells the person, and keeps it for next time', () => {
    vi.useFakeTimers()
    let tick = 0
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => window.setTimeout(() => { tick += 100; cb(tick) }, 0))      // 10 frames a second
    vi.stubGlobal('cancelAnimationFrame', (id: number) => window.clearTimeout(id))
    function Slow() { const { mode, degrade } = useFps(); useFpsWatchdog(mode !== 'off', 24, degrade, mode); return <Mode /> }
    render(<EffectsProvider><Slow /><EffectsControl lang="en" /></EffectsProvider>)
    expect(screen.getByTestId('mode')).toHaveTextContent('full')
    act(() => { vi.advanceTimersByTime(2000 + 4000) })
    expect(screen.getByTestId('mode')).toHaveTextContent('reduced')
    expect(screen.getByRole('status')).toHaveTextContent(FXTEXT.en.auto); expect(localStorage.getItem('cs-fx')).toBe('reduced')
    act(() => { vi.advanceTimersByTime(2000 + 4000) })
    expect(screen.getByTestId('mode')).toHaveTextContent('off')                                // still too slow: switch the effects off
  })

  it('stays at full on a fast screen', () => {
    vi.useFakeTimers()
    let tick = 0
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => window.setTimeout(() => { tick += 16; cb(tick) }, 0))        // about 60 frames a second
    vi.stubGlobal('cancelAnimationFrame', (id: number) => window.clearTimeout(id))
    const slow = vi.fn()
    function Fast() { useFpsWatchdog(true, 24, slow); return null }
    render(<Fast />)
    act(() => { vi.advanceTimersByTime(2000 + 5000) })
    expect(slow).not.toHaveBeenCalled()
  })
})

describe('the holographic phone', () => {
  it('keeps the live call usable: its buttons stay reachable and clickable inside the card', () => {
    const onEnd = vi.fn()
    render(<EffectsProvider><PhoneFrame level="high" label="Phone"><button type="button" onClick={onEnd}>End call</button></PhoneFrame></EffectsProvider>)
    expect(screen.getByRole('group', { name: 'Phone' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'End call' }))
    expect(onEnd).toHaveBeenCalled()
  })

  it('is a plain phone when effects are off', () => {
    localStorage.setItem('cs-fx', 'off')
    const { container } = render(<EffectsProvider><PhoneFrame level="low" label="Phone"><p>screen</p></PhoneFrame></EffectsProvider>)
    expect(container.querySelector('.phone')).toBeTruthy(); expect(container.querySelector('.holo-card')).toBeNull()
  })

  it('a card is an image for assistive technology only when it holds no content', () => {
    const { rerender } = render(<HoloCard alt="Card" />)
    expect(screen.getByRole('img', { name: 'Card' })).toBeTruthy()
    rerender(<HoloCard alt="Card"><p>live</p></HoloCard>)
    expect(screen.getByRole('group', { name: 'Card' })).toBeTruthy()
  })

  it('draws no body image where canvas is missing, and the screen window sits inside the card', () => {
    expect(phoneBezel()).toBe('')                                                              // jsdom has no canvas: the screen simply has no metal frame
    expect(PHONE_RATIO).toBeCloseTo(0.62, 2)
    const left = parseFloat(SCREEN.left), width = parseFloat(SCREEN.width), top = parseFloat(SCREEN.top), height = parseFloat(SCREEN.height)
    expect(left * 2 + width).toBeCloseTo(100, 3); expect(top * 2 + height).toBeCloseTo(100, 3)       // centred window
  })
})

describe('glitch panels', () => {
  it('draw behind a panel in the tone of the risk, and disappear when effects are off', () => {
    const { unmount } = render(<EffectsProvider><GlitchLayer tone="high" /></EffectsProvider>)
    expect(screen.getByTestId('fx-glitch')).toHaveAttribute('data-tone', 'high')
    unmount(); localStorage.setItem('cs-fx', 'off')
    render(<EffectsProvider><GlitchLayer tone="alert" /></EffectsProvider>)
    expect(screen.queryByTestId('fx-glitch')).toBeNull()
  })
})
