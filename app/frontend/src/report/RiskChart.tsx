import { useRef } from 'react'
import { fmtCall } from './derive'
import type { RiskPoint, SessionEvent, Source } from './types'

interface Props {
  duration: number; risk: RiskPoint[]; events: SessionEvent[]; cursor: number | null; label: string
  onSeek: (t: number) => void; onPick: (e: SessionEvent) => void; describe: (e: SessionEvent) => string
}

const W = 800, H = 230, L = 34, R = 12, T = 12, BOTTOM = 170, LANE = 200
const COLOR: Record<Source, string> = { rules: 'var(--elevated)', model: '#8b5cf6', alert: 'var(--high)', connection: 'var(--neutral)', voice: '#14b8a6', system: 'var(--mut)' }

/** Risk over time: the line draws itself in, the area glows, event dots pop in one after another and the playhead glides while replaying. */
export default function RiskChart({ duration, risk, events, cursor, label, onSeek, onPick, describe }: Props) {
  const ref = useRef<SVGSVGElement>(null)
  const dur = Math.max(duration, 1)
  const x = (t: number) => L + (Math.min(Math.max(t, 0), dur) / dur) * (W - L - R)
  const y = (score: number) => BOTTOM - (Math.min(Math.max(score, 0), 10) / 10) * (BOTTOM - T)
  const pts = risk.length ? risk : [{ t: 0, level: 'low' as const, score: 0, model: null }]
  let d = `M${x(0)},${y(pts[0].score)}`
  pts.forEach((p) => { d += ` H${x(p.t)} V${y(p.score)}` })
  d += ` H${x(dur)}`
  const area = `${d} V${y(0)} H${x(0)} Z`

  const seekFromPointer = (clientX: number) => {
    const box = ref.current?.getBoundingClientRect()
    if (!box || box.width === 0) return
    const frac = ((clientX - box.left) / box.width) * W
    onSeek(Math.min(dur, Math.max(0, ((frac - L) / (W - L - R)) * dur)))
  }
  const onKey = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 5 : 1
    const now = cursor ?? 0
    if (e.key === 'ArrowRight') onSeek(Math.min(dur, now + step))
    else if (e.key === 'ArrowLeft') onSeek(Math.max(0, now - step))
    else if (e.key === 'Home') onSeek(0)
    else if (e.key === 'End') onSeek(dur)
    else return
    e.preventDefault()
  }

  return (
    <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="rp-chart" role="slider" tabIndex={0} aria-label={label} aria-valuemin={0} aria-valuemax={Math.round(dur)}
         aria-valuenow={Math.round(cursor ?? 0)} aria-valuetext={fmtCall(cursor ?? 0)} data-testid="rp-chart" onKeyDown={onKey}
         onPointerDown={(e) => { (e.currentTarget as Element).setPointerCapture?.(e.pointerId); seekFromPointer(e.clientX) }}
         onPointerMove={(e) => { if (e.buttons === 1) seekFromPointer(e.clientX) }}>
      <defs>
        <linearGradient id="rp-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.45" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect x={L} y={y(10)} width={W - L - R} height={y(6) - y(10)} className="rp-zone high" />
      <rect x={L} y={y(6)} width={W - L - R} height={y(3) - y(6)} className="rp-zone elevated" />
      {[0, 3, 6, 10].map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeDasharray={v === 3 || v === 6 ? '4 4' : undefined} />
          <text x={L - 6} y={y(v) + 4} fontSize="11" textAnchor="end" fill="var(--mut)">{v}</text>
        </g>
      ))}
      <path d={area} className="rp-area" fill="url(#rp-fill)" />
      <path d={d} className="rp-line" pathLength={1} fill="none" strokeWidth="2.75" strokeLinejoin="round" strokeLinecap="round" />
      <line x1={L} x2={W - R} y1={LANE} y2={LANE} stroke="var(--line)" />
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <text key={f} x={x(dur * f)} y={H - 4} fontSize="11" textAnchor="middle" fill="var(--mut)">{fmtCall(dur * f).replace(/\.\d$/, '')}</text>
      ))}
      {events.map((e, idx) => (
        <circle key={e.i} cx={x(e.t)} cy={LANE} r="5.5" fill={COLOR[e.source] ?? 'var(--mut)'} stroke="var(--card)" strokeWidth="1.5"
                className={`rp-dot${cursor !== null && e.t <= cursor ? ' passed' : ''}`} style={{ ['--i' as string]: Math.min(idx, 24) } as React.CSSProperties}
                data-testid="rp-dot" onPointerDown={(ev) => ev.stopPropagation()} onClick={() => onPick(e)}>
          <title>{`${fmtCall(e.t)}  ${describe(e)}`}</title>
        </circle>
      ))}
      {cursor !== null && (
        <g className="rp-playhead" style={{ transform: `translateX(${x(cursor)}px)` }} data-testid="rp-cursor-line">
          <line x1="0" x2="0" y1={T} y2={LANE + 8} />
          <circle cx="0" cy={T} r="5" />
        </g>
      )}
    </svg>
  )
}
