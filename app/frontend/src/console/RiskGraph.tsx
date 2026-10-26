import { useState } from 'react'
import { categoryText, type Dict } from '../i18n'
import type { LiveEvent, LivePoint } from '../live/state'
import type { Level } from '../types'
import { formatClock } from './derive'

interface Props { t: Dict; history: LivePoint[]; events: LiveEvent[]; level: Level; score: number }

const W = 640, H = 250, ML = 34, MR = 12, MT = 16, MB = 30

/** Risk score over the call, coloured by level, with alert markers. Hover or focus a point to see what was heard there. Plain SVG. */
export default function RiskGraph({ t, history, events, level, score }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const c = t.console
  const last = history.length ? history[history.length - 1].t : 0
  const step = last > 150 ? 60 : last > 60 ? 30 : 15
  const tMax = Math.max(60, Math.ceil((last + 8) / step) * step)
  const x = (tt: number) => ML + (Math.min(tt, tMax) / tMax) * (W - ML - MR)
  const y = (s: number) => MT + (1 - Math.min(10, Math.max(0, s)) / 10) * (H - MT - MB)
  const ticks: number[] = []
  for (let s = 0; s <= tMax; s += step) ticks.push(s)
  const alerts = events.filter((e) => e.kind === 'alert')
  const tip = hover !== null ? history[hover] : null

  return (
    <div className="graph" data-testid="risk-graph">
      {history.length === 0 ? <p className="mut graph-empty">{c.graphEmpty}</p> : (
        <div className="graph-frame">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={c.graphLabel(t.levels[level], score)} onMouseLeave={() => setHover(null)}
               onMouseMove={(e) => {
                 const r = e.currentTarget.getBoundingClientRect()
                 if (r.width <= 0) return
                 const vx = ((e.clientX - r.left) / r.width) * W
                 let best = 0
                 history.forEach((p, i) => { if (Math.abs(x(p.t) - vx) < Math.abs(x(history[best].t) - vx)) best = i })
                 setHover(best)
               }}>
            {[0, 5, 10].map((g) => (
              <g key={g}>
                <line x1={ML} x2={W - MR} y1={y(g)} y2={y(g)} className="gridline" />
                <text x={ML - 6} y={y(g) + 4} className="axis" textAnchor="end">{g}</text>
              </g>
            ))}
            {ticks.map((s) => <text key={s} x={x(s)} y={H - 8} className="axis" textAnchor="middle">{formatClock(s)}</text>)}
            {history.length > 1 && (
              <polygon className={`area ${level}`} points={`${x(history[0].t)},${y(0)} ${history.map((p) => `${x(p.t)},${y(p.score)}`).join(' ')} ${x(last)},${y(0)}`} />
            )}
            {history.slice(1).map((p, i) => (
              <line key={i} x1={x(history[i].t)} y1={y(history[i].score)} x2={x(p.t)} y2={y(p.score)} pathLength={1} className={`seg ${p.level}`} />
            ))}
            {alerts.map((e) => (
              <g key={e.id} className={`marker ${e.alertLevel}`} data-testid={`marker-${e.alertLevel}`}>
                <line x1={x(e.t)} x2={x(e.t)} y1={MT} y2={H - MB} />
                <text x={Math.min(x(e.t) + 4, W - 70)} y={MT + 10}>{e.alertLevel === 'high' ? c.markerHigh : c.markerElevated}</text>
              </g>
            ))}
            {history.map((p, i) => (
              <circle key={i} cx={x(p.t)} cy={y(p.score)} r={hover === i ? 6 : 3.5} className={`pt ${p.level}${i === history.length - 1 ? ' latest' : ''}`}
                      tabIndex={p.fresh.length > 0 || i === history.length - 1 ? 0 : -1} data-testid="graph-point"
                      aria-label={`${formatClock(p.t)}, ${c.tipScore(p.score)}`}
                      onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
            ))}
          </svg>
          {tip && (
            <div className="graph-tip" role="status" data-testid="graph-tip" style={{ left: `${Math.min(78, Math.max(2, (x(tip.t) / W) * 100 - 10))}%` }}>
              <strong>{formatClock(tip.t)}</strong> · {c.tipScore(tip.score)} · <span className={`lvl ${tip.level}`}>{t.levels[tip.level]}</span>
              {tip.fresh.length === 0 ? <div className="mut">{c.noNewEvidence}</div> : (
                <ul>{tip.fresh.map((f, i) => <li key={i}>“{f.quote}” <span className="mut">{categoryText(t, f.category).label}</span></li>)}</ul>
              )}
            </div>
          )}
        </div>
      )}
      <p className="mut"><small>{c.axisNote}</small></p>
    </div>
  )
}
