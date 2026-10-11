import type { Dict } from '../i18n'
import type { AnalysisSummary } from '../types'

interface Props {
  t: Dict
  items: AnalysisSummary[]
  onOpen: (id: string) => void
  onDelete: (id: string) => void
  onDeleteAll: () => void
}

export default function HistoryList({ t, items, onOpen, onDelete, onDeleteAll }: Props) {
  return (
    <section className="card" aria-labelledby="hist-title">
      <div className="row">
        <h2 id="hist-title">{t.history}</h2>
        {items.length > 0 && <button type="button" className="button danger small" onClick={onDeleteAll}>{t.deleteAll}</button>}
      </div>
      {items.length === 0 ? <p className="mut">{t.noHistory}</p> : (
        <ul className="history">
          {items.map((it) => (
            <li key={it.id}>
              <div>
                <strong className="filename">{it.filename}</strong>
                <div className="mut">{new Date(it.created).toLocaleString()}</div>
              </div>
              <span className={`badge ${it.status === 'done' && it.level ? it.level : 'neutral'}`}>
                {it.status === 'done' && it.level ? t.levels[it.level]
                  : it.status === 'error' ? t.failedTitle
                  : t.steps[(it.step ?? 'queued') as keyof Dict['steps']]}
              </span>
              <div className="actions">
                <button type="button" className="button secondary small" onClick={() => onOpen(it.id)}>{t.open}</button>
                <button type="button" className="button danger small" onClick={() => onDelete(it.id)}>{t.delete}</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
