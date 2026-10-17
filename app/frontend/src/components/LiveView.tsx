import { splitTranscript } from '../highlight'
import { categoryText, type Dict } from '../i18n'
import type { LiveState } from '../live/state'

interface Props {
  t: Dict
  state: LiveState
  onOpenReport: (id: string) => void
  onAgain: () => void
  /** Show the "what to do now" suggestions (call mode on the Receiver). */
  advice?: boolean
}

/** Presentational part of the live check: meter, alert, evidence and transcript. */
export default function LiveView({ t, state, onOpenReport, onAgain, advice = false }: Props) {
  const l = t.live
  const status = { idle: '', connecting: l.connecting, waiting: t.call.waitingSpeaker, joined: t.call.speakerJoined, live: l.listening, stopping: l.stopping, ended: '', error: '' }[state.status]
  const limit = state.warning?.startsWith('limit:') ? Number(state.warning.slice(6)) : null
  return (
    <section className="card" aria-live="polite">
      {status && <p className="big" data-testid="live-status">{status} {state.seconds > 0 && <span className="mut">{Math.round(state.seconds)}s</span>}</p>}

      {state.alert && (
        <p className={`notice ${state.alert === 'high' ? 'warn' : ''} alert-banner`} role="alert" data-testid="live-alert">
          {state.alert === 'high' ? l.alertHigh : l.alertElevated}
        </p>
      )}

      <div className="meter-row">
        <span>{l.meter}</span>
        <div className="meter" role="meter" aria-label={l.meter} aria-valuemin={0} aria-valuemax={10} aria-valuenow={state.score}>
          <div className={`meter-bar ${state.level}`} style={{ width: `${Math.min(10, state.score) * 10}%` }} />
        </div>
        <span className={`badge ${state.level}`} data-testid="live-level">{t.levels[state.level]}</span>
      </div>

      {advice && state.tracks.length > 0 && (
        <div className="advice" data-testid="live-advice">
          <h4>{t.whatToDo}</h4>
          <ul>{t.advice[state.level].map((a, i) => <li key={i}>{a}</li>)}</ul>
        </div>
      )}

      {state.hits.length > 0 && (
        <>
          <h4>{l.spotted}</h4>
          <ul className="evidence">
            {state.hits.map((h, i) => (
              <li key={i}>
                <span className={`tag ${h.kind}`}>{t.legend[h.kind]}</span> <strong>{categoryText(t, h.category, h.explanation).label}</strong>
                <q>{h.quote}</q>
              </li>
            ))}
          </ul>
        </>
      )}

      <h4>{t.transcript}</h4>
      {state.tracks.length === 0 ? <p className="mut">{l.waiting}</p> : state.tracks.map((tr) => (
        <div key={tr.code}>
          {state.tracks.length > 1 && <h5 className="mut">{tr.code}</h5>}
          <p className="tx">
            {splitTranscript(tr.text, tr.hits).map((seg, i) =>
              seg.hit ? <mark key={i} className={`mark ${seg.hit.kind}`}>{seg.text}</mark> : <span key={i}>{seg.text}</span>)}
          </p>
        </div>
      ))}

      {state.warning && !limit && <p className="notice"><small>{l.warningNote}</small></p>}
      {limit !== null && <p className="notice warn">{l.limitReached(limit)}</p>}
      {state.status === 'error' && <p className="notice warn" role="alert" data-testid="live-error">{state.message}</p>}
      {state.status === 'ended' && (
        <div className="toolbar">
          {state.id ? <button type="button" className="button primary" onClick={() => onOpenReport(state.id!)}>{l.openReport}</button>
                    : <p className="notice">{state.message ?? l.tooShort}</p>}
          <button type="button" className="button secondary" onClick={onAgain}>{l.again}</button>
        </div>
      )}
    </section>
  )
}
