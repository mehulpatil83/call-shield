import type { Level } from '../types'
import { useAnimatedNumber } from './useAnimatedNumber'

interface Props { label: string; level: Level; score: number }

/** The risk meter: a glowing track in three zones (0-3 low, 3-6 elevated, 6-10 high) with a thumb that glides to the score. */
export default function RiskSlider({ label, level, score }: Props) {
  const shown = useAnimatedNumber(score, 900)
  const pct = Math.min(10, Math.max(0, score)) * 10
  return (
    <div className={`meter slider ${level}`} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={10} aria-valuenow={score}
         aria-valuetext={`${score} / 10`}>
      <div className="slider-zones" aria-hidden="true"><i /><i /><i /></div>
      <div className={`meter-bar ${level}`} style={{ width: `${pct}%` }} />
      <div className={`slider-thumb ${level}`} style={{ left: `${pct}%` }} aria-hidden="true"><span>{shown.toFixed(1)}</span></div>
    </div>
  )
}
