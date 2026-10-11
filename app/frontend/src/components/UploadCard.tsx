import { useRef, useState } from 'react'
import type { Dict } from '../i18n'
import type { SpeechLang } from '../types'

const ACCEPT = '.wav,.mp3,.m4a,.flac,.ogg,audio/*'

interface Props {
  t: Dict
  maxMb: number
  keyPresent: boolean
  busy: boolean
  onSubmit: (file: File, language: SpeechLang, consent: boolean, skipAudio: boolean) => void
}

export default function UploadCard({ t, maxMb, keyPresent, busy, onSubmit }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState<SpeechLang>('en')
  const [consent, setConsent] = useState(false)
  const [skipAudio, setSkipAudio] = useState(false)
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  const tooBig = file !== null && file.size > maxMb * 1024 * 1024
  const ready = file !== null && consent && !tooBig && !busy

  return (
    <section className="card" aria-labelledby="upload-title">
      <h2 id="upload-title">{t.uploadTitle}</h2>
      {!keyPresent && <p className="notice warn" role="alert">{t.keyMissing}</p>}

      <div
        className={`drop${dragging ? ' dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const f = e.dataTransfer.files?.[0]
          if (f) setFile(f)
        }}
      >
        <input
          ref={input}
          id="audio-file"
          type="file"
          accept={ACCEPT}
          className="visually-hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <label htmlFor="audio-file" className="button secondary">{t.chooseFile}</label>
        <p className="mut">{t.dropHint}</p>
        <p className="filename" aria-live="polite">{file ? file.name : t.noFile}</p>
        {tooBig && <p className="notice warn" role="alert">{t.tooBig(maxMb)}</p>}
      </div>

      <label className="field">
        <span>{t.languageLabel}</span>
        <select value={language} onChange={(e) => setLanguage(e.target.value as SpeechLang)}>
          {(Object.keys(t.langs) as SpeechLang[]).map((k) => (
            <option key={k} value={k}>{t.langs[k]}</option>
          ))}
        </select>
      </label>

      <label className="check">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>{t.consent}</span>
      </label>
      <label className="check">
        <input type="checkbox" checked={skipAudio} onChange={(e) => setSkipAudio(e.target.checked)} />
        <span>{t.skipAudio}</span>
      </label>

      <button
        type="button"
        className="button primary"
        disabled={!ready}
        onClick={() => file && onSubmit(file, language, consent, skipAudio)}
      >
        {busy ? t.working : t.analyse}
      </button>
    </section>
  )
}
