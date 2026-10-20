import { useEffect, useState } from 'react'
import * as api from '../api'
import CallConsole from '../console/CallConsole'
import PresenterDrawer from '../console/PresenterDrawer'
import type { Dict } from '../i18n'
import { type ReceiverDeps, useCallReceiver } from '../call/useCallReceiver'
import type { SpeechLang } from '../types'
import QrCode from './QrCode'

interface Props {
  t: Dict
  onOpenReport: (id: string) => void
  deps?: ReceiverDeps
  loadConfig?: () => Promise<{ public_url: string | null }>
}

/** Receiver screen (this computer): start a call, show the code and QR for the phone, then the call console. */
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
  const waiting = state.status === 'waiting' || state.status === 'joined' || (state.status === 'connecting' && info !== null)
  const inConsole = info !== null && ['live', 'reconnecting', 'stopping', 'ended', 'error'].includes(state.status)

  // once the call is running: the call console (live analysis + phone simulation) takes the whole width
  if (inConsole) {
    return (
      <div className="console-wrap">
        <CallConsole t={t} state={state} language={(info!.language as SpeechLang) ?? language} listening={listening} audio={audio}
                     onListen={setListen} onEnd={end} onAgain={reset} onOpenReport={onOpenReport} />
      </div>
    )
  }

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
            <PresenterDrawer t={t} />
          </>
        )}
        {state.status === 'error' && !info && <p className="notice warn" role="alert" data-testid="call-error">{state.message}</p>}
      </section>

      {info && waiting && (
        <section className="card call-share" aria-live="polite">
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
        </section>
      )}
    </>
  )
}
