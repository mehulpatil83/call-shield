import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Ring from './Ring'
import RiskSlider from './RiskSlider'
import { useAnimatedNumber } from './useAnimatedNumber'

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

function Probe({ target }: { target: number }) {
  return <span data-testid="n">{useAnimatedNumber(target, 500).toFixed(2)}</span>
}

describe('animated risk slider', () => {
  it('exposes the true score to assistive technology and moves the fill and the thumb to it', () => {
    render(<RiskSlider label="Risk so far" level="elevated" score={4.5} />)
    const meter = screen.getByRole('meter', { name: 'Risk so far' })
    expect(meter).toHaveAttribute('aria-valuenow', '4.5'); expect(meter).toHaveAttribute('aria-valuetext', '4.5 / 10')
    expect(meter.querySelector('.meter-bar')).toHaveStyle({ width: '45%' })
    expect(meter.querySelector('.slider-thumb')).toHaveStyle({ left: '45%' })
    expect(meter.className).toContain('elevated')
  })
  it('keeps the fill inside the track for out-of-range scores', () => {
    render(<RiskSlider label="r" level="high" score={14} />)
    expect(screen.getByRole('meter').querySelector('.meter-bar')).toHaveStyle({ width: '100%' })
  })
})

describe('useAnimatedNumber', () => {
  it('counts up to the target and stops there', async () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance', 'setTimeout', 'clearTimeout'] })
    render(<Probe target={8} />)
    expect(Number(screen.getByTestId('n').textContent)).toBeLessThan(8)
    await act(async () => { await vi.advanceTimersByTimeAsync(900) })
    expect(screen.getByTestId('n')).toHaveTextContent('8.00')
  })
  it('jumps at once when the person prefers reduced motion', () => {
    const original = window.matchMedia
    window.matchMedia = (() => ({ matches: true })) as unknown as typeof window.matchMedia          // jsdom has no matchMedia
    try {
      render(<Probe target={6} />)
      expect(screen.getByTestId('n')).toHaveTextContent('6.00')
    } finally {
      window.matchMedia = original
    }
  })
})

describe('Ring', () => {
  it('describes itself and sweeps its arc to the value', async () => {
    vi.useFakeTimers()
    render(<Ring value={0.5} label="50%" caption="Model" tone="elevated" />)
    expect(screen.getByRole('img', { name: 'Model: 50%' })).toBeTruthy()
    const arc = document.querySelector('.ring-arc') as SVGCircleElement
    const full = Number(arc.getAttribute('stroke-dasharray'))
    expect(Number(arc.getAttribute('stroke-dashoffset'))).toBeCloseTo(full)            // starts empty
    await act(async () => { await vi.advanceTimersByTimeAsync(100) })
    expect(Number(arc.getAttribute('stroke-dashoffset'))).toBeCloseTo(full * 0.5)      // sweeps to half
  })
})
