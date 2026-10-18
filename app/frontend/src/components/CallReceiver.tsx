import { useEffect, useState } from 'react'
import * as api from '../api'
import type { Dict } from '../i18n'
import { type ReceiverDeps, useCallReceiver } from '../call/useCallReceiver'
import type { SpeechLang } from '../types'
import LiveView from './LiveView'
import QrCode from './QrCode'

interface Props {
  t: Dict
  onOpenReport: (id: string) => void
  deps?: ReceiverDeps
  loadConfig?: () => Promise<{ public_url: string | null }>
}

/** Receiver screen (this computer): start a call, show the code and QR for the phone, then the live check. */
export default function CallReceiver({ t, onOpenReport, deps, loadConfig = api.callConfig }: Props) {
  const { state, info, listening, audio, start, setListen, end, reset } = useCallReceiver(deps)
  const c = t.call
  const [language, setLanguage] = useState<SpeechLang>('en')
  const [consent, setConsent] = useState(false)
  const [skipAudio, setSkipAudio] = useState(false)
  const [publicUrl, setPublicUrl] = useState('')

  useEffect(() => {
    let stop = false
    loadConfig().then((cfg) => { if (!stop && cfg.public_url) setPublicUrl((cur) => cur || cfg.public_url!) }).catch(() => undefined)
    try { const saved = localStorage.getItem('cs-public-url'); if (saved) setPublicUrl((cur) => cur || saved) } catch { /* ignore */ }
    return () => { stop = true }
  }, [loadConfig])

  const begin = () => {
    try { if (publicUrl) localStorage.setItem('cs-public-url', publicUrl) } catch { /* ignore */ }
    void start(language, skipAudio, publicUrl.trim() || null)
  }
  const idle = state.status === 'idle'
  const inCall = state.status === 'live' || state.status === 'reconnecting' || state.status === 'stopping'
  const waiting = state.status === 'waiting' || state.status === 'joined' || (state.status === 'connecting' && info !== null)

  return (
    <>
      <section className="card" aria-labelledby="call-title">
        <h2 id="call-title">{c.title}</h2>
        <p>{c.intro}</p>
        {idle && (
          <>
            <label className="field">
              <span>{t.languageLabel}</span>
              <select value={language} onChange={(e) => setLanguage(e.target.value as SpeechLang)}>
                {(Object.keys(t.langs) as SpeechLang[]).map((k) => <option key={k} value={k}>{t.langs[k]}</option>)}
              </select>
            </label>
            <label className="field">
              <span>{c.publicLabel}</span>
              <input type="url" inputMode="url" placeholder="https://…trycloudflare.com" value={publicUrl} onChange={(e) => setPublicUrl(e.target.value)} />
              <small className="mut">{c.publicHint}</small>
            </label>
            {!publicUrl.trim() && <p className="notice">{c.noTunnel}</p>}
            <label className="check">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>{c.consent}</span>
            </label>
            <label className="check">
              <input type="checkbox" checked={skipAudio} onChange={(e) => setSkipAudio(e.target.checked)} />
              <span>{t.skipAudio}</span>
            </label>
            <div className="toolbar">
              <button type="button" className="button primary" disabled={!consent} onClick={begin}>{c.start}</button>
            </div>
          </>
        )}
        {state.status === 'error' && !info && <p className="notice warn" role="alert" data-testid="call-error">{state.message}</p>}
      </section>

      {info && (waiting || inCall) && (
        <section className="card call-share" aria-live="polite">
          {waiting && (
            <>
              <p className="big" data-testid="call-status">{state.status === 'joined' ? c.speakerJoined : c.waitingSpeaker}</p>
              <p>{c.scan}</p>
              <div className="share-row">
                {info.join_url && <QrCode value={info.join_url} label={c.joinAddress} />}
                <div>
                  <p className="mut">{c.codeLabel}</p>
                  <p className="code" data-testid="call-code">{info.code}</p>
                  {info.join_url ? <p className="filename"><small>{c.joinAddress}: <code data-testid="call-join-url">{info.join_url}</code></small></p>
                                 : <p className="notice">{c.noTunnel}</p>}
                  <p className="mut"><small>{c.expires(Math.round(info.expires_in / 60))}</small></p>
                </div>
              </div>
              <div className="toolbar"><button type="button" className="button secondary" onClick={end}>{c.cancel}</button></div>
            </>
          )}
          {inCall && (
            <>
              {state.status === 'reconnecting' ? (
                <p className="notice warn" role="status" data-testid="call-reconnecting">{c.receiverReconnecting(60)}</p>
              ) : (
                <div className="audio-status" data-testid="call-audio" data-state={audio.state}>
                  <div className="levelbar small" role="meter" aria-label={c.audioLevelLabel} aria-valuemin={0} aria-valuemax={100}
                       aria-valuenow={Math.round(audio.level * 100)}>
                    <div className="levelfill" style={{ width: `${Math.round(audio.level * 100)}%` }} />
                  </div>
                  <p className={audio.state === 'ok' ? 'mut' : 'notice warn'} role="status">
                    {audio.state === 'ok' ? c.receivingAudio : audio.state === 'silent' ? c.audioSilent : c.audioNone}
                  </p>
                </div>
              )}
              <label className="check">
                <input type="checkbox" checked={listening} onChange={(e) => setListen(e.target.checked)} />
                <span>{c.listen}</span>
              </label>
              <p className="mut"><small>{c.listenHint}</small></p>
              <div className="toolbar">
                <button type="button" className="button danger" disabled={state.status === 'stopping'} onClick={end}>{c.end}</button>
              </div>
            </>
          )}
        </section>
      )}

      {(inCall || state.status === 'ended' || (state.status === 'error' && info !== null)) && (
        <LiveView t={t} state={state} advice onOpenReport={onOpenReport} onAgain={reset} />
      )}
    </>
  )
}
