import { useState } from 'react'
import { reportHtmlUrl } from '../api'
import { splitTranscript } from '../highlight'
import { categoryText, type Dict } from '../i18n'
import type { AnalysisDetail, Hit } from '../types'
import ScoreChart from './ScoreChart'

interface Props {
  detail: AnalysisDetail
  t: Dict
  onDelete: () => void
  onBack: () => void
}

export default function ReportView({ detail, t, onDelete, onBack }: Props) {
  const report = detail.report
  const [active, setActive] = useState<{ ti: number; hit: Hit } | null>(null)
  if (!report) return null
  const { conversation: conv, authenticity: auth } = report
  const level = conv.level
  const shownHits = conv.hits

  return (
    <article className="report">
      <div className="toolbar">
        <button type="button" className="button secondary" onClick={onBack}>{t.back}</button>
        <a className="button secondary" href={reportHtmlUrl(detail.id)}>{t.download}</a>
        <button type="button" className="button danger" onClick={onDelete}>{t.delete}</button>
      </div>

      <h2 className="filename">{detail.filename}</h2>
      <p className="mut">{new Date(report.meta.created).toLocaleString()} · {report.meta.language}
        {report.meta.audio_seconds ? ` · ${report.meta.audio_seconds}s` : ''}
        {report.meta.est_cost_rupees ? ` · ₹${report.meta.est_cost_rupees}` : ''}</p>

      <p className="plain" data-testid="plain-summary">{t.plain[level]}</p>
      <section className="card advice" aria-labelledby="todo-title">
        <h3 id="todo-title">{t.whatToDo}</h3>
        <ul>{t.advice[level].map((a) => <li key={a}>{a}</li>)}</ul>
      </section>

      <div className="grid">
        <section className="card" aria-labelledby="conv-title">
          <h3 id="conv-title">1. {t.conversation}</h3>
          <p><span className={`badge ${level}`} data-testid="level-badge">{t.levels[level]}</span></p>
          <h4>{t.evidence}</h4>
          {shownHits.length === 0 ? <p>{t.noEvidence}</p> : (
            <ul className="evidence">
              {shownHits.map((h, i) => {
                const c = categoryText(t, h.category, h.explanation)
                return (
                  <li key={i}>
                    <span className={`tag ${h.kind}`}>{t.legend[h.kind]}</span>{' '}
                    <strong>{c.label}</strong>
                    <q>{h.quote}</q>
                    <small>{c.explain}</small>
                  </li>
                )
              })}
            </ul>
          )}
          {conv.digit_runs.length > 0 && (
            <>
              <h4>{t.spokenNumbers}</h4>
              <p><small>{t.digitNote}</small></p>
              <ul>{conv.digit_runs.map((d, i) => <li key={i}><q>{d.quote}</q> ({t.digitsCount(d.digits.length)})</li>)}</ul>
            </>
          )}
        </section>

        <section className="card" aria-labelledby="auth-title">
          <h3 id="auth-title">2. {t.authenticity}</h3>
          {auth === null ? <p>–</p> : (
            <>
              <p className="big">{t.auth[(auth.code || 'unavailable') as keyof Dict['auth']]}</p>
              {auth.median !== null && <p>{t.medianLine(auth.median, auth.q25 ?? auth.median, auth.q75 ?? auth.median, auth.n_windows)}</p>}
              {auth.status === 'unavailable' && auth.reason && <p><small>{auth.reason}</small></p>}
              <ScoreChart auth={auth} t={t} />
              <p><small>{t.authNote}</small></p>
              <p><small>{t.provisional}</small></p>
            </>
          )}
        </section>
      </div>

      <section className="card" aria-labelledby="tx-title">
        <h3 id="tx-title">{t.transcript}</h3>
        <p className="mut">{t.transcriptHint}</p>
        <p className="legend">
          {(['request', 'pressure', 'context', 'warning'] as const).map((k) => (
            <span key={k} className={`mark ${k}`}>{t.legend[k]}</span>
          ))}
        </p>
        {report.transcripts.map((tr, ti) => (
          <div key={ti}>
            {report.transcripts.length > 1 && <h4>{tr.code}</h4>}
            <p className="tx" lang={tr.code.startsWith('mr') ? 'mr' : tr.code.startsWith('hi') ? 'hi' : 'en'}>
              {splitTranscript(tr.text, tr.rules.hits).map((seg, si) =>
                seg.hit ? (
                  <button
                    type="button"
                    key={si}
                    className={`mark ${seg.hit.kind}`}
                    aria-pressed={active?.hit === seg.hit}
                    onClick={() => setActive({ ti, hit: seg.hit! })}
                  >{seg.text}</button>
                ) : <span key={si}>{seg.text}</span>)}
            </p>
            {active?.ti === ti && (
              <p className="notice" role="status" data-testid="hit-reason">
                <strong>{categoryText(t, active.hit.category, active.hit.explanation).label}.</strong>{' '}
                {categoryText(t, active.hit.category, active.hit.explanation).explain}
              </p>
            )}
          </div>
        ))}
      </section>

      <section className="card" aria-labelledby="lim-title">
        <h3 id="lim-title">{t.limitations}</h3>
        <ul>{t.limits.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
    </article>
  )
}
