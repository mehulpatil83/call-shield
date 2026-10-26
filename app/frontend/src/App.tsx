import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import CallReceiver from './components/CallReceiver'
import HistoryList from './components/HistoryList'
import LivePanel from './components/LivePanel'
import ProgressCard from './components/ProgressCard'
import ReportView from './components/ReportView'
import ReportPage from './report/ReportPage'
import AppBackdrop from './ui/fx/Backdrop'
import EffectsControl from './ui/fx/EffectsControl'
import { EffectsProvider } from './ui/fx/effects'
import GlitchLayer from './ui/fx/GlitchLayer'
import { RTEXT } from './report/strings'
import SpeakerPage from './components/SpeakerPage'
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

type Route = { name: 'home' } | { name: 'live' } | { name: 'call' } | { name: 'join'; code: string } | { name: 'analysis'; id: string } | { name: 'report'; id: string }

function readRoute(): Route {
  const h = window.location.hash
  if (h === '#/live') return { name: 'live' }
  if (h === '#/call') return { name: 'call' }
  const code = /^#\/join\/(\d{0,6})$/.exec(h)?.[1]
  if (code !== undefined) return { name: 'join', code }
  const rid = /^#\/r\/([a-f0-9]{12})$/.exec(h)?.[1]
  if (rid) return { name: 'report', id: rid }
  const id = /^#\/a\/([a-f0-9]{12})$/.exec(h)?.[1]
  return id ? { name: 'analysis', id } : { name: 'home' }
}

function useRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(readRoute)
  useEffect(() => {
    const on = () => setRoute(readRoute())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return [route, (next) => {
    window.location.hash = next.name === 'analysis' ? `#/a/${next.id}` : next.name === 'report' ? `#/r/${next.id}` : next.name === 'live' ? '#/live' : next.name === 'call' ? '#/call' : next.name === 'join' ? `#/join/${next.code}` : ''
  }]
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
  const live = Boolean((detail.report?.meta as { live?: boolean } | undefined)?.live)
  return <ReportView detail={detail} t={t} onDelete={remove} onBack={onBack} timelineLabel={live ? RTEXT[lang].title : undefined} />
}

function LocalAppInner() {
  const [lang, setLang] = useLang()
  const t = STRINGS[lang]
  const [route, setRoute] = useRoute()
  const id = route.name === 'analysis' ? route.id : null
  const setId = (next: string | null) => setRoute(next ? { name: 'analysis', id: next } : { name: 'home' })
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
  useEffect(() => { if (route.name === 'home') refresh() }, [route.name, refresh])
  useEffect(() => { document.documentElement.lang = lang }, [lang])

  const submit = async (file: File, language: SpeechLang, consent: boolean, skip: boolean, conversation: boolean) => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.createAnalysis(file, language, consent, skip, conversation)
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
      <header className="top has-fx">
        <GlitchLayer tone="low" />
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
        <EffectsControl lang={lang} />
      </header>
      <nav className="tabs" aria-label="Main">
        <button type="button" className={`tab${route.name === 'home' || route.name === 'analysis' ? ' active' : ''}`} aria-current={route.name === 'home' || route.name === 'analysis' ? 'page' : undefined}
                onClick={() => setRoute({ name: 'home' })}>{t.nav.upload}</button>
        <button type="button" className={`tab${route.name === 'live' ? ' active' : ''}`} aria-current={route.name === 'live' ? 'page' : undefined}
                onClick={() => setRoute({ name: 'live' })}>{t.nav.live}</button>
        <button type="button" className={`tab${route.name === 'call' || route.name === 'join' ? ' active' : ''}`} aria-current={route.name === 'call' || route.name === 'join' ? 'page' : undefined}
                onClick={() => setRoute({ name: 'call' })}>{t.nav.call}</button>
      </nav>
      <p className="notice">{t.privacy}</p>
      {error && <p className="notice warn" role="alert">{error}</p>}

      {route.name === 'live' ? (
        <LivePanel t={t} onOpenReport={(rid) => setRoute({ name: 'report', id: rid })} />
      ) : route.name === 'call' ? (
        <CallReceiver t={t} onOpenReport={(rid) => setRoute({ name: 'report', id: rid })} />
      ) : route.name === 'join' ? (
        <SpeakerPage t={t} initialCode={route.code} />
      ) : route.name === 'report' ? (
        <ReportPage id={route.id} lang={lang} onBack={() => setRoute({ name: 'home' })}
                    onTechnical={() => setRoute({ name: 'analysis', id: route.id })} onDeleted={() => setRoute({ name: 'home' })} />
      ) : id ? (
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

const LOCAL_NAMES = ['127.0.0.1', 'localhost']

/** The phone opens the tunnel address: it only ever gets the Speaker screen (the server allows nothing else there). */
export function SpeakerApp() {
  const [lang, setLang] = useLang()
  const t = STRINGS[lang]
  useEffect(() => { document.documentElement.lang = lang }, [lang])
  const code = /^#\/join\/(\d{0,6})$/.exec(window.location.hash)?.[1] ?? ''
  return (
    <div className="page phone">
      <header className="top">
        <div>
          <h1>{t.appName}</h1>
          <p className="mut">{t.call.roleSpeaker}</p>
        </div>
        <label className="field compact">
          <span className="visually-hidden">{t.interfaceLanguage}</span>
          <select aria-label={t.interfaceLanguage} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
            {(Object.keys(LANG_NAMES) as Lang[]).map((k) => <option key={k} value={k}>{LANG_NAMES[k]}</option>)}
          </select>
        </label>
      </header>
      <SpeakerPage t={t} initialCode={code} />
    </div>
  )
}

function LocalApp() {
  return (
    <EffectsProvider>
      <AppBackdrop />
      <LocalAppInner />
    </EffectsProvider>
  )
}

export default function App() {
  return LOCAL_NAMES.includes(window.location.hostname) ? <LocalApp /> : <SpeakerApp />
}
