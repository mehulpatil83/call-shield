import type { Dict } from '../i18n'
import type { Step } from '../types'

const ORDER: Step[] = ['transcribing', 'analysing', 'checking_audio']

export default function ProgressCard({ t, step }: { t: Dict; step: Step | null }) {
  const at = step ? ORDER.indexOf(step) : -1
  return (
    <section className="card" aria-live="polite" aria-busy="true">
      <h2>{t.working}</h2>
      <ol className="steps">
        {ORDER.map((s, i) => (
          <li key={s} className={i < at ? 'done' : i === at ? 'active' : ''}>
            {i < at ? '✓ ' : i === at ? '… ' : ''}{t.steps[s]}
          </li>
        ))}
      </ol>
    </section>
  )
}
