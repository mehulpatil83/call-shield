import { useEffect, useRef, useState } from 'react'

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** A number that eases towards `target` (count-up). With reduced motion, or where animation frames do not exist, it jumps at once. */
export function useAnimatedNumber(target: number, ms = 800, from = 0): number {
  const [value, setValue] = useState(from)
  const current = useRef(from)
  useEffect(() => {
    if (prefersReducedMotion() || typeof requestAnimationFrame === 'undefined') {
      current.current = target
      setValue(target)
      return
    }
    const start = current.current
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms)
      current.current = start + (target - start) * (1 - Math.pow(1 - p, 3))
      setValue(current.current)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return value
}
