import { useEffect, useState } from 'react'

interface Props { value: number; label: string; caption: string; tone: 'low' | 'elevated' | 'high' | 'neutral' }

/** A ring gauge (0..1) whose arc sweeps in when it appears. */
export default function Ring({ value, label, caption, tone }: Props) {
  const [drawn, setDrawn] = useState(0)
  useEffect(() => {
    const id = window.setTimeout(() => setDrawn(Math.min(1, Math.max(0, value))), 60)
    return () => window.clearTimeout(id)
  }, [value])
  const R = 34, C = 2 * Math.PI * R
  return (
    <div className={`ring ${tone}`} role="img" aria-label={`${caption}: ${label}`}>
      <svg viewBox="0 0 84 84" aria-hidden="true">
        <circle className="ring-track" cx="42" cy="42" r={R} />
        <circle className="ring-arc" cx="42" cy="42" r={R} strokeDasharray={C} strokeDashoffset={C * (1 - drawn)} transform="rotate(-90 42 42)" />
      </svg>
      <span className="ring-label">{label}</span>
    </div>
  )
}
