import { useState } from 'react'
import { AlertSettingsPanel } from '../alert/AlertOverlay'
import { useAlertExperience } from '../alert/useAlertExperience'
import type { AudioState } from '../call/useCallReceiver'
import { categoryText, type Dict } from '../i18n'
import type { LiveEvent, LiveState } from '../live/state'
import type { SpeechLang } from '../types'
import { TACTICS, estimateRupees, formatClock, heardCategories, scorecard, wantsNow } from './derive'
import PhoneSim, { type Focus } from './PhoneSim'
import PresenterDrawer from './PresenterDrawer'
import RiskGraph from './RiskGraph'
import { useElapsed } from './useElapsed'

interface Props {
  t: Dict
  state: LiveState
  language: SpeechLang
  listening: boolean
  audio: { state: AudioState; level: number }
  onListen: (on: boolean) => void
  onEnd: () => void
  onAgain: () => void
  onOpenReport: (id: string) => void
}

/** The call console: live analysis on the left, a phone call simulation on the right. */
export default function CallConsole({ t, state, language, listening, audio, onListen, onEnd, onAgain, onOpenReport }: Props) {
  const c = t.console
  const ax = useAlertExperience(t, state)
  const elapsed = useElapsed(state.status)
  const [selected, setSelected] = useState<string | null>(null)
  const ended = state.status === 'ended'
  const live = state.status === 'live' || state.status === 'stopping'
  const seconds = Math.max(elapsed, state.seconds)

  const mdl = state.model
  const modelText = !mdl ? '—' : mdl.status === 'off' ? c.modelOff : mdl.status === 'loading' ? c.modelLoading : mdl.status === 'unavailable' ? c.modelUnavailable
    : mdl.prob === null ? '—' : c.modelProb(Math.round(mdl.peak * 100)) + (mdl.raised ? c.modelRaised : '')

  const heard = heardCategories(state.events)
  const wants = wantsNow(state.events)
  const chosen: LiveEvent | undefined = state.events.find((e) => e.id === selected)
  const focus: Focus | null = chosen?.kind === 'tactic' ? { category: chosen.category!, quote: chosen.quote! } : null
  const timeline = [...state.events].sort((a, b) => a.t - b.t)
  const card = ended ? scorecard(state) : null
  const takeover = ax.shown === 'high' && ax.settings.fullscreen
  const strip = ax.shown === 'elevated' || (ax.shown === 'high' && !ax.settings.fullscreen)
  const limit = state.warning?.startsWith('limit:') ? Number(state.warning.slice(6)) : null
  const when = (s: number | null) => (s === null ? c.notReached : c.after(Math.round(s)))

  return (
    <div className="console" data-testid="console">
      <div className="console-left">
        <section className="card console-head" aria-live="polite">
          <div className="console-head-row">
            <span className={`live-dot${ended ? ' off' : ''}`} aria-hidden="true" />
            <strong data-testid="console-state">{ended ? c.ended : c.live}</strong>
            <span className="timer-small" data-testid="console-time">{formatClock(seconds)}</span>
            <span className="mut">{t.langs[language]}</span>
          </div>
          <div className="meter-row">
            <span>{t.live.meter}</span>
            <div className="meter" role="meter" aria-label={t.live.meter} aria-valuemin={0} aria-valuemax={10} aria-valuenow={state.score}>
              <div className={`meter-bar ${state.level}`} style={{ width: `${Math.min(10, state.score) * 10}%` }} />
            </div>
            <span className={`badge ${state.level}`} data-testid="live-level">{t.levels[state.level]}</span>
          </div>
          {state.alert && (
            <p className={`notice ${state.alert === 'high' ? 'warn' : ''}`} role="alert" data-testid="live-alert">
              {state.alert === 'high' ? t.live.alertHigh : t.live.alertElevated}
            </p>
          )}
          {state.status === 'reconnecting' ? (
            <p className="notice warn" role="status" data-testid="call-reconnecting">{t.call.receiverReconnecting(60)}</p>
          ) : live && (
            <div className="audio-status" data-testid="call-audio" data-state={audio.state}>
              <div className="levelbar small" role="meter" aria-label={t.call.audioLevelLabel} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(audio.level * 100)}>
                <div className="levelfill" style={{ width: `${Math.round(audio.level * 100)}%` }} />
              </div>
              <p className={audio.state === 'ok' ? 'mut' : 'notice warn'} role="status">
                {audio.state === 'ok' ? t.call.receivingAudio : audio.state === 'silent' ? t.call.audioSilent : t.call.audioNone}
              </p>
            </div>
          )}
          {live && (
            <>
              <label className="check"><input type="checkbox" checked={listening} onChange={(e) => onListen(e.target.checked)} /><span>{t.call.listen}</span></label>
              <p className="mut"><small>{t.call.listenHint}</small></p>
              <div className="toolbar"><button type="button" className="button danger" disabled={state.status === 'stopping'} onClick={onEnd}>{t.call.end}</button></div>
            </>
          )}
          {state.warning && !limit && <p className="notice"><small>{t.live.warningNote}</small></p>}
          {limit !== null && <p className="notice warn">{t.live.limitReached(limit)}</p>}
          {state.status === 'error' && <p className="notice warn" role="alert" data-testid="live-error">{state.message}</p>}
        </section>

        {card && (
          <section className="card scorecard" aria-labelledby="sc-title" data-testid="scorecard">
            <h3 id="sc-title">{c.scorecardTitle}</h3>
            <dl>
              <div><dt>{c.verdict}</dt><dd><span className={`badge ${card.verdict}`} data-testid="sc-verdict">{t.levels[card.verdict]}</span></dd></div>
              <div><dt>{c.firstWarning}</dt><dd data-testid="sc-warning">{when(card.firstWarningAt)}</dd></div>
              <div><dt>{c.highAlert}</dt><dd data-testid="sc-high">{when(card.highAlertAt)}</dd></div>
              <div><dt>{c.firstAsk}</dt><dd data-testid="sc-ask">{when(card.firstRequestAt)}</dd></div>
              <div><dt>{c.duration}</dt><dd>{formatClock(Math.max(card.duration, elapsed))}</dd></div>
              <div><dt>{c.peak}</dt><dd>{card.peakScore} / 10</dd></div>
              <div><dt>{c.tacticsHeard}</dt><dd data-testid="sc-tactics">{card.tactics.length ? card.tactics.map((k) => categoryText(t, k).label).join(', ') : c.noTactics}</dd></div>
            </dl>
            <p className="mut"><small>{c.timesNote}</small></p>
            <div className="toolbar">
              {state.id ? <button type="button" className="button primary" onClick={() => onOpenReport(state.id!)}>{t.live.openReport}</button>
                        : <p className="notice">{state.message ?? t.live.tooShort}</p>}
              <button type="button" className="button secondary" onClick={onAgain}>{t.live.again}</button>
            </div>
          </section>
        )}

        <section className="card" aria-labelledby="rg-title">
          <h3 id="rg-title">{c.riskTitle}</h3>
          <RiskGraph t={t} history={state.history} events={state.events} level={state.level} score={state.score} />
        </section>

        <div className="console-pair">
          <section className="card" aria-labelledby="wants-title">
            <h3 id="wants-title">{c.wantsTitle}</h3>
            {wants.length === 0 ? <p className="mut" data-testid="wants-none">{c.wantsNothing}</p> : (
              <ul className="wants" data-testid="wants">{wants.map((k) => <li key={k}>{c.wants[k] ?? categoryText(t, k).label}</li>)}</ul>
            )}
          </section>
          {state.tracks.length > 0 && (
            <section className="card advice" data-testid="live-advice">
              <h3>{t.whatToDo}</h3>
              <ul>{t.advice[state.level].map((a, i) => <li key={i}>{a}</li>)}</ul>
            </section>
          )}
        </div>

        <section className="card" aria-labelledby="tac-title">
          <h3 id="tac-title">{c.tacticsTitle}</h3>
          <ul className="tactics" data-testid="tactics">
            {TACTICS.map((k) => (
              <li key={k.id} className={`tactic ${k.kind}${heard.has(k.id) ? ' on' : ''}`} data-on={heard.has(k.id)}>{categoryText(t, k.id).label}</li>
            ))}
          </ul>
        </section>

        <section className="card" aria-labelledby="tl-title">
          <h3 id="tl-title">{c.timelineTitle}</h3>
          {timeline.length === 0 ? <p className="mut">{c.timelineEmpty}</p> : (
            <>
              <p className="mut"><small>{c.timelineHint}</small></p>
              <ol className="timeline" data-testid="timeline">
                {timeline.map((e) => (
                  <li key={e.id}>
                    <button type="button" className={`tl-item ${e.kind === 'alert' ? `alert ${e.alertLevel}` : e.hitKind}${selected === e.id ? ' sel' : ''}`}
                            aria-pressed={selected === e.id} onClick={() => setSelected(selected === e.id ? null : e.id)}>
                      <span className="tl-time">{formatClock(e.t)}</span>
                      {e.kind === 'alert'
                        ? <span>{c.alertFired(t.levels[e.alertLevel!])}</span>
                        : <span><strong>{categoryText(t, e.category!).label}</strong> <q>{e.quote}</q></span>}
                    </button>
                  </li>
                ))}
              </ol>
              {chosen && (
                <div className="why" data-testid="why">
                  <h4>{c.whyTitle}</h4>
                  <p>{chosen.kind === 'tactic' ? categoryText(t, chosen.category!).explain : chosen.alertLevel === 'high' ? t.live.alertHigh : t.live.alertElevated}</p>
                </div>
              )}
            </>
          )}
        </section>

        <section className="card" aria-labelledby="det-title">
          <h3 id="det-title">{c.detailsTitle}</h3>
          <dl className="details">
            <div><dt>{c.duration}</dt><dd>{formatClock(seconds)}</dd></div>
            <div><dt>{c.cost}</dt><dd data-testid="cost">₹{estimateRupees(seconds, language).toFixed(2)} <small className="mut">{c.costNote}</small></dd></div>
            <div><dt>{c.engine}</dt><dd>{c.engineValue}</dd></div>
            <div><dt>{c.modelRow}</dt><dd data-testid="model-row">{modelText}</dd></div>
            <div><dt>{c.voice}</dt><dd>{c.voiceValue}</dd></div>
          </dl>
          <AlertSettingsPanel t={t} settings={ax.settings} onChange={ax.change} fullscreenLabel={c.takeoverLabel} />
        </section>

        <PresenterDrawer t={t} />
      </div>

      <div className="console-right">
        <PhoneSim t={t} state={state} elapsed={seconds} listening={listening} takeover={takeover} strip={strip} voice={ax.voice} focus={focus}
                  onToggleListen={() => onListen(!listening)} onEnd={onEnd} onDismiss={ax.dismiss} onRepeat={ax.repeat} />
      </div>
    </div>
  )
}
