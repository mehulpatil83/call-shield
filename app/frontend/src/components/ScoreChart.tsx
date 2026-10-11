import type { Dict } from '../i18n'
import type { Authenticity } from '../types'

const LO = -11
const HI = 3
const W = 300
const H = 110

export default function ScoreChart({ auth, t }: { auth: Authenticity; t: Dict }) {
  const scores = auth.window_scores
  if (!scores.length) return null
  const y = (v: number) => H - ((Math.max(LO, Math.min(HI, v)) - LO) / (HI - LO)) * H
  const bw = Math.max(8, Math.min(30, Math.floor((W - 12) / scores.length) - 4))
  const label = `${t.chartTitle}: ${scores.join(', ')}`
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {[[auth.real_at_least, '#2e7d32', t.bandNatural], [auth.synth_at_most, '#c62828', t.bandSynthetic]].map(([v, colour, text]) => (
          <g key={String(text)}>
            <line x1={0} x2={W} y1={y(v as number)} y2={y(v as number)} stroke={colour as string} strokeDasharray="4 3" />
            <text x={2} y={y(v as number) - 3} fontSize={9} fill={colour as string}>{text as string}</text>
          </g>
        ))}
        {scores.map((v, i) => (
          <rect key={i} x={8 + i * (bw + 4)} y={y(v)} width={bw} height={Math.max(1, H - y(v))} fill="#5c6bc0">
            <title>{`#${i + 1}: ${v}`}</title>
          </rect>
        ))}
      </svg>
      <figcaption>{t.chartTitle}</figcaption>
    </figure>
  )
}
