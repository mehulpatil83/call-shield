import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Level } from '../../types'
import HoloCard from './HoloCard'
import { PHONE_LOOK } from './atmosphere'
import { useFx } from './effects'
import { PHONE_RATIO, SCREEN, SCREEN_FRAME, phoneBezel } from './phoneBezel'

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

function useViewportHeight(): number {
  const [h, setH] = useState(() => (typeof window === 'undefined' ? 800 : window.innerHeight))
  useEffect(() => {
    const on = () => setH(window.innerHeight)
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return h
}

/** The phone body: a holographic card whose screen is the live call. Plain CSS phone when effects are off. */
export default function PhoneFrame({ level, label, children }: { level: Level; label: string; children: ReactNode }) {
  const { mode } = useFx()
  const vh = useViewportHeight()
  const bezel = useMemo(() => phoneBezel(), [])
  if (mode === 'off') return <div className="phone">{children}</div>
  const width = clamp(Math.round(vh * 0.8 * PHONE_RATIO), 300, 390)
  const look = PHONE_LOOK[level]
  return (
    <div className="phone-holo">
      <HoloCard
        image={bezel || undefined} aspect={PHONE_RATIO} width={width} radius={Math.round(width * 0.12)} alt={label}
        preset={look.preset} foilColor={look.foil} intensity={look.intensity} edgeSparkle={0.6} frame={SCREEN_FRAME} glare={0.35}
        tiltMax={mode === 'reduced' ? 0 : 7} hoverScale={1.01} idle={false} shadow screen={SCREEN}
      >
        {children}
      </HoloCard>
    </div>
  )
}
