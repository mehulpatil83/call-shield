import { useRef, useState } from 'react'
import type { Dict } from '../i18n'
import { useLive } from '../live/useLive'
import type { SpeechLang } from '../types'
import LiveView from './LiveView'

interface Props {
  t: Dict
  onOpenReport: (id: string) => void
  createSocket?: (url: string) => WebSocket
}

export default function LivePanel({ t, onOpenReport, createSocket }: Props) {
  const { state, startMic, replay, stop, reset } = useLive(createSocket)
  const [language, setLanguage] = useState<SpeechLang>('auto')
  const [consent, setConsent] = useState(false)
  const [skipAudio, setSkipAudio] = useState(false)
  const file = useRef<HTMLInputElement>(null)
  const running = state.status === 'connecting' || state.status === 'live' || state.status === 'stopping'
  const l = t.live

  return (
    <>
      <section className="card" aria-labelledby="live-title">
        <h2 id="live-title">{l.title}</h2>
        <p>{l.intro}</p>
        <p className="mut"><small>{l.micHint}</small></p>
        <label className="field">
          <span>{t.languageLabel}</span>
          <select value={language} disabled={running} onChange={(e) => setLanguage(e.target.value as SpeechLang)}>
            {(Object.keys(t.langs) as SpeechLang[]).map((k) => <option key={k} value={k}>{t.langs[k]}</option>)}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={consent} disabled={running} onChange={(e) => setConsent(e.target.checked)} />
          <span>{t.consent}</span>
        </label>
        <label className="check">
          <input type="checkbox" checked={skipAudio} disabled={running} onChange={(e) => setSkipAudio(e.target.checked)} />
          <span>{t.skipAudio}</span>
        </label>
        <div className="toolbar">
          <button type="button" className="button primary" disabled={!consent || running} onClick={() => startMic(language, skipAudio)}>{l.startMic}</button>
          <input
            ref={file} type="file" accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg" className="visually-hidden" data-testid="replay-input"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) replay(f, language, skipAudio); e.target.value = '' }}
          />
          <button type="button" className="button secondary" disabled={!consent || running} onClick={() => file.current?.click()}>{l.replay}</button>
          {running && <button type="button" className="button danger" onClick={stop}>{l.stop}</button>}
        </div>
      </section>
      {state.status !== 'idle' && <LiveView t={t} state={state} onOpenReport={onOpenReport} onAgain={reset} />}
    </>
  )
}
