import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import HistoryList from './components/HistoryList'
import ProgressCard from './components/ProgressCard'
import ReportView from './components/ReportView'
import UploadCard from './components/UploadCard'
import { LANG_NAMES, STRINGS } from './i18n'
import type { AnalysisDetail, AnalysisSummary, Health, Lang, SpeechLang } from './types'

function useLang(): [Lang, (l: Lang) => void] {
  const [lang, set] = useState<Lang>(() => {
    try {
      const v = localStorage.getItem('cs-lang')
      if (v === 'en' || v === 'hi' || v === 'mr') return v
    } catch { /* storage may be unavailable */ }
    return 'en'
  })
  return [lang, (l) => {
    set(l)
    try { localStorage.setItem('cs-lang', l) } catch { /* ignore */ }
  }]
}

function useHashId(): [string | null, (id: string | null) => void] {
  const read = () => /^#\/a\/([a-f0-9]{12})$/.exec(window.location.hash)?.[1] ?? null
  const [id, setId] = useState<string | null>(read)
  useEffect(() => {
    const on = () => setId(read())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return [id, (next) => { window.location.hash = next ? `#/a/${next}` : '' }]
}

function AnalysisView({ id, lang, onBack }: { id: string; lang: Lang; onBack: () => void }) {
  const t = STRINGS[lang]
  const [detail, setDetail] = useState<AnalysisDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let stop = false
    let timer: number | undefined
    const tick = async () => {
      try {
        const d = await api.getAnalysis(id)
        if (stop) return
        setDetail(d)
        if (d.status === 'queued' || d.status === 'running') timer = window.setTimeout(tick, 1200)
      } catch (e) {
        if (!stop) setError(e instanceof Error ? e.message : String(e))
      }
    }
    tick()
    return () => { stop = true; if (timer) window.clearTimeout(timer) }
  }, [id])

  const remove = async () => {
    if (!window.confirm(t.confirmDelete)) return
    await api.deleteAnalysis(id)
    onBack()
  }

  if (error) return <section className="card"><p className="notice warn" role="alert">{error}</p><button type="button" className="button secondary" onClick={onBack}>{t.back}</button></section>
  if (!detail) return <section className="card"><p>{t.working}</p></section>
  if (detail.status === 'queued' || detail.status === 'running') return <ProgressCard t={t} step={detail.step} />
  if (detail.status === 'error') {
    return (
      <section className="card">
        <h2>{t.failedTitle}</h2>
        <p className="notice warn" role="alert">{detail.error}</p>
        <div className="toolbar">
          <button type="button" className="button secondary" onClick={onBack}>{t.back}</button>
          <button type="button" className="button danger" onClick={remove}>{t.delete}</button>
        </div>
      </section>
    )
  }
  return <ReportView detail={detail} t={t} onDelete={remove} onBack={onBack} />
}

export default function App() {
  const [lang, setLang] = useLang()
  const t = STRINGS[lang]
  const [id, setId] = useHashId()
  const [health, setHealth] = useState<Health | null>(null)
  const [items, setItems] = useState<AnalysisSummary[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try { setItems(await api.listAnalyses()) } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }, [])

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])
  useEffect(() => { if (!id) refresh() }, [id, refresh])
  useEffect(() => { document.documentElement.lang = lang }, [lang])

  const submit = async (file: File, language: SpeechLang, consent: boolean, skip: boolean) => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.createAnalysis(file, language, consent, skip)
      setId(r.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const removeOne = async (rid: string) => {
    if (!window.confirm(t.confirmDelete)) return
    await api.deleteAnalysis(rid)
    refresh()
  }
  const removeAll = async () => {
    if (!window.confirm(t.confirmDeleteAll)) return
    await api.deleteAll()
    refresh()
  }

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>{t.appName}</h1>
          <p className="mut">{t.tagline}</p>
        </div>
        <label className="field compact">
          <span className="visually-hidden">{t.interfaceLanguage}</span>
          <select aria-label={t.interfaceLanguage} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
            {(Object.keys(LANG_NAMES) as Lang[]).map((k) => <option key={k} value={k}>{LANG_NAMES[k]}</option>)}
          </select>
        </label>
      </header>
      <p className="notice">{t.privacy}</p>
      {error && <p className="notice warn" role="alert">{error}</p>}

      {id ? (
        <AnalysisView id={id} lang={lang} onBack={() => setId(null)} />
      ) : (
        <>
          <UploadCard t={t} maxMb={health?.max_upload_mb ?? 25} keyPresent={health?.gnani_key_present ?? true}
                      busy={busy} onSubmit={submit} />
          <HistoryList t={t} items={items} onOpen={(rid) => setId(rid)} onDelete={removeOne} onDeleteAll={removeAll} />
        </>
      )}
    </div>
  )
}
