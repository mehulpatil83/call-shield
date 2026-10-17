import { useState } from 'react'
import type { Dict } from '../i18n'
import { type SpeakerDeps, useSpeaker } from '../call/useSpeaker'

interface Props { t: Dict; initialCode?: string; deps?: SpeakerDeps }

const clock = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

/** Speaker screen (the phone): a plain call screen. It never shows any analysis. */
export default function SpeakerPage({ t, initialCode = '', deps }: Props) {
  const c = t.call
  const { state, join, toggleMute, leave, reset } = useSpeaker(deps)
  const [code, setCode] = useState(initialCode)
  const [consent, setConsent] = useState(false)
  const valid = /^\d{6}$/.test(code)
  const inCall = state.status === 'connecting' || state.status === 'live'
  const errorText = state.error === 'mic' ? c.micDenied : state.error === 'connection' ? c.lostConnection : state.message

  if (inCall) {
    return (
      <section className="card callscreen" aria-live="polite">
        <div className="avatar" aria-hidden="true">📞</div>
        <p className="big" data-testid="speaker-status">{state.status === 'live' ? c.connected : c.connecting}</p>
        <p className="timer" data-testid="speaker-timer">{clock(state.seconds)}</p>
        {state.muted && <p className="mut">{c.muted}</p>}
        <p className="mut"><small>{c.nothingShown}</small></p>
        <p className="mut"><small>{c.keepScreenOn}</small></p>
        <div className="call-buttons">
          <button type="button" className={`round${state.muted ? ' on' : ''}`} aria-pressed={state.muted} disabled={state.status !== 'live'} onClick={toggleMute}>
            {state.muted ? c.unmute : c.mute}
          </button>
          <button type="button" className="round end" onClick={leave}>{c.endCall}</button>
        </div>
      </section>
    )
  }

  if (state.status === 'ended') {
    return (
      <section className="card callscreen">
        <p className="big" data-testid="speaker-ended">{c.ended}</p>
        <div className="toolbar"><button type="button" className="button primary" onClick={reset}>{c.joinAnother}</button></div>
      </section>
    )
  }

  return (
    <section className="card" aria-labelledby="speak-title">
      <h2 id="speak-title">{c.speakerTitle}</h2>
      <p>{c.speakerIntro}</p>
      <label className="field">
        <span>{c.codeInput}</span>
        <input className="code-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
               onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
      </label>
      {code.length > 0 && !valid && <p className="mut"><small>{c.codeInvalid}</small></p>}
      <label className="check">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>{c.speakerConsent}</span>
      </label>
      {state.status === 'error' && <p className="notice warn" role="alert" data-testid="speaker-error">{errorText}</p>}
      <div className="toolbar">
        <button type="button" className="button primary big-button" disabled={!valid || !consent} onClick={() => join(code)}>{c.join}</button>
      </div>
    </section>
  )
}
