import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../api'
import { LANG_NAMES, STRINGS, categoryText } from '../i18n'
import type { Lang } from '../types'
import { useAtmosphere } from '../ui/fx/effects'
import GlitchLayer from '../ui/fx/GlitchLayer'
import Ring from '../ui/Ring'
import { currentIndex, decidedBy, describe, filterEvents, firstSentence, fmtCall, fmtClock, markQuotes, modelRaisedAt, primaryTrack, rulesLevel, stats, type Filters } from './derive'
import RiskChart from './RiskChart'
import { RTEXT } from './strings'
import { SOURCES, type AiResult, type SessionEvent, type SessionResponse, type Source } from './types'

interface Props {
  id: string; lang: Lang; onBack: () => void; onTechnical: () => void; onDeleted: () => void
  load?: (id: string) => Promise<SessionResponse>
  writeAi?: (id: string, lang: Lang, consent: boolean, force: boolean) => Promise<{ ai: AiResult; cached: boolean }>
}

const store = {
  get: (k: string) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* storage may be unavailable */ } },
}

export default function ReportPage({ id, lang, onBack, onTechnical, onDeleted, load = api.getSession, writeAi = api.writeAi }: Props) {
  const t = STRINGS[lang]
  const r = RTEXT[lang]
  const [data, setData] = useState<SessionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cursor, setCursor] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(2)
  const [filters, setFilters] = useState<Filters>({ sources: new Set(SOURCES), category: null, query: '' })
  const [track, setTrack] = useState<string | null>(null)
  const [aiMap, setAiMap] = useState<Record<string, AiResult>>({})
  const [aiBusy, setAiBusy] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [consent, setConsent] = useState(() => store.get('cs-ai-consent') === '1')
  const [auto, setAuto] = useState(() => store.get('cs-ai-auto') === '1')
  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let stop = false
    load(id).then((d) => { if (!stop) { setData(d); setAiMap(d.ai) } }).catch((e) => { if (!stop) setError(e instanceof Error ? e.message : String(e)) })
    return () => { stop = true }
  }, [id, load])

  const session = data?.session ?? null
  useAtmosphere(session?.max_level ?? 'low')
  const dur = session?.duration ?? 0

  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => {
      setCursor((c) => {
        const next = (c ?? 0) + 0.1 * speed
        if (next >= dur) { setPlaying(false); return dur }
        return next
      })
    }, 100)
    return () => window.clearInterval(timer)
  }, [playing, speed, dur])

  const askAi = useCallback(async (force: boolean) => {
    setAiBusy(true)
    setAiError(null)
    try {
      const res = await writeAi(id, lang, true, force)
      setAiMap((m) => ({ ...m, [lang]: res.ai }))
    } catch (e) {
      setAiError(e instanceof Error ? e.message : String(e))
    } finally {
      setAiBusy(false)
    }
  }, [id, lang, writeAi])

  const autoTried = useRef<string | null>(null)
  useEffect(() => {      // the automatic option: once per language, only if the person already agreed
    if (data?.ai_status.configured && auto && consent && !aiMap[lang] && autoTried.current !== lang) {
      autoTried.current = lang
      void askAi(false)
    }
  }, [data, auto, consent, aiMap, lang, askAi])

  const allEvents = session?.events ?? []
  const shown = useMemo(() => filterEvents(allEvents, filters, r, t), [allEvents, filters, r, t])
  const cur = currentIndex(shown, cursor)
  const tracks = useMemo(() => Array.from(new Set((session?.segments ?? []).map((s) => s.track))), [session])
  const mainTrack = track ?? primaryTrack(session?.segments ?? [])
  const quotesByTrack = useMemo(() => allEvents.filter((e) => e.kind === 'tactic' && e.quote && (!mainTrack || !e.track || e.track === mainTrack)).map((e) => e.quote!), [allEvents, mainTrack])
  const q = filters.query.trim().toLowerCase()
  const segments = (session?.segments ?? []).filter((s) => s.track === mainTrack && (!q || s.text.toLowerCase().includes(q)))
  const currentSeg = cursor === null ? -1 : segments.reduce((acc, s, i) => (s.first_t <= cursor ? i : acc), -1)

  useEffect(() => {
    if (currentSeg < 0) return
    const el = transcriptRef.current?.querySelector<HTMLElement>(`[data-seg="${currentSeg}"]`)
    el?.scrollIntoView?.({ block: 'nearest' })
  }, [currentSeg])

  if (error) return <section className="card"><p className="notice warn" role="alert">{r.loadError} {error}</p><button type="button" className="button secondary" onClick={onBack}>{r.back}</button></section>
  if (!session || !data) return <section className="card skeleton-card" aria-busy="true"><p>{r.loading}</p><div className="skeleton" /><div className="skeleton short" /><div className="skeleton" /></section>

  const st = stats(session)
  const when = (v: number | null) => (v === null ? r.notReached : fmtCall(v))
  const ai = aiMap[lang]
  const rLevel = rulesLevel(session)
  const decided = decidedBy(session)
  const raisedAt = modelRaisedAt(session)
  const modelPct = st.modelPeak === null ? null : Math.round(st.modelPeak * 100)
  const modelTone = st.modelPeak === null ? 'neutral' : st.modelPeak >= 0.95 ? 'high' : st.modelPeak >= 0.85 ? 'elevated' : 'low'
  const decidedText = decided.by === 'none' ? r.combined.decidedNone : decided.by === 'model' ? r.combined.decidedModel(fmtCall(decided.at ?? 0)) : r.combined.decidedRules
  const toggleSource = (s: Source) => setFilters((f) => { const next = new Set(f.sources); if (next.has(s)) next.delete(s); else next.add(s); return { ...f, sources: next } })
  const seek = (v: number) => { setPlaying(false); setCursor(v) }
  const pick = (e: SessionEvent) => seek(e.t)
  const categories = Array.from(new Set(allEvents.filter((e) => e.kind === 'tactic' && e.category).map((e) => e.category!)))
  const download = () => {
    const blob = new Blob([JSON.stringify({ session, ai: aiMap }, null, 1)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `call-shield-${id}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const remove = async () => {
    if (!window.confirm(r.deleteConfirm)) return
    await api.deleteAnalysis(id)
    onDeleted()
  }
  const seekToQuote = (quote: string) => {
    const seg = session.segments.find((s) => s.text.toLowerCase().includes(quote.toLowerCase()))
    if (seg) seek(seg.first_t)
  }

  return (
    <article className="report rp" data-testid="report-page">
      <div className="toolbar no-print">
        <button type="button" className="button secondary" onClick={onBack}>{r.back}</button>
        <button type="button" className="button secondary" onClick={onTechnical}>{r.technical}</button>
        <button type="button" className="button secondary" onClick={() => window.print()}>{r.print}</button>
        <button type="button" className="button secondary" onClick={download}>{r.exportJson}</button>
        <button type="button" className="button danger" onClick={remove}>{r.delete}</button>
      </div>

      <h2>{r.title}</h2>
      <p className="mut">{new Date(session.started_at).toLocaleString()}</p>

      <section className="card rp-stats has-fx" aria-label={r.verdict}>
        <GlitchLayer tone={st.maxLevel} interactive={false} />
        <dl>
          <div><dt>{r.verdict}</dt><dd><span className={`badge ${st.maxLevel}`} data-testid="rp-verdict">{t.levels[st.maxLevel]}</span></dd></div>
          <div><dt>{r.duration}</dt><dd>{fmtCall(st.duration)}</dd></div>
          <div><dt>{r.firstAlert}</dt><dd data-testid="rp-first-alert">{when(st.firstAlertAt)}</dd></div>
          <div><dt>{r.highAt}</dt><dd data-testid="rp-high-at">{when(st.highAt)}</dd></div>
          <div><dt>{r.tactics}</dt><dd>{st.tactics.length ? st.tactics.map((k) => categoryText(t, k).label).join(', ') : r.none}</dd></div>
          <div><dt>{r.modelPeak}</dt><dd>{st.modelPeak === null ? '—' : `${Math.round(st.modelPeak * 100)}%`}</dd></div>
          <div><dt>{r.voice}</dt><dd>{st.voice ?? '—'}</dd></div>
        </dl>
      </section>


      <section className="card combined" aria-labelledby="cmb-title" data-testid="rp-combined">
        <div className="cmb-head">
          <div><h3 id="cmb-title">{r.combined.title}</h3><p className="mut"><small>{r.combined.sub}</small></p></div>
          <div className="cmb-final">
            <span className="mut">{r.combined.final}</span>
            <span className={`badge big ${st.maxLevel}`}>{t.levels[st.maxLevel]}</span>
            <small data-testid="rp-decided">{decidedText}</small>
          </div>
        </div>
        <div className="cmb-grid">
          <article className="cmb-panel" data-testid="cmb-rules">
            <h4>{r.combined.rules}</h4><p className="mut"><small>{r.combined.rulesDesc}</small></p>
            <p><span className={`badge ${rLevel}`}>{t.levels[rLevel]}</span> <small className="mut">{r.combined.tactics(st.tactics.length)}</small></p>
            <p className="chips">{st.tactics.length === 0 ? <small className="mut">{r.none}</small> : st.tactics.map((k) => (
              <span key={k} className="chip static" title={allEvents.find((e) => e.kind === 'tactic' && e.category === k)?.quote}>{categoryText(t, k).label}</span>))}</p>
          </article>
          <article className="cmb-panel" data-testid="cmb-model">
            <h4>{r.combined.model}</h4><p className="mut"><small>{r.combined.modelDesc}</small></p>
            <div className="cmb-ring">
              <Ring value={st.modelPeak ?? 0} label={modelPct === null ? '—' : `${modelPct}%`} caption={r.modelPeak} tone={modelTone as 'low' | 'elevated' | 'high' | 'neutral'} />
              <p>{modelPct === null ? r.combined.modelNone : raisedAt !== null ? r.combined.modelRaised(fmtCall(raisedAt)) : r.combined.modelAgrees}</p>
            </div>
          </article>
          <article className="cmb-panel" data-testid="cmb-ai">
            <h4>{r.combined.ai}</h4><p className="mut"><small>{r.combined.aiDesc}</small></p>
            {ai ? <p className="plain">{firstSentence(ai.summary)}</p>
              : aiBusy ? <p className="mut shimmer-text">{r.combined.aiWaiting}</p>
              : <p className="mut">{data.ai_status.configured ? r.combined.aiCta : r.ai.notSet}</p>}
          </article>
        </div>
      </section>

      <section className="card" aria-labelledby="rp-quick">
        <h3 id="rp-quick">{r.quickTitle}</h3>
        <p data-testid="rp-quick">{r.quick({ duration: fmtCall(st.duration), level: r.levelShort[st.maxLevel], firstAlert: st.firstAlertAt === null ? null : fmtCall(st.firstAlertAt),
          tactics: st.tactics.map((k) => categoryText(t, k).label) })}</p>
      </section>

      <section className="card rp-ai" aria-labelledby="rp-ai-title" data-testid="rp-ai">
        <h3 id="rp-ai-title">{r.ai.title} <small className="mut">({LANG_NAMES[lang]})</small></h3>
        {!data.ai_status.configured && <><p className="notice">{r.ai.notSet}</p><p className="mut"><small>{r.ai.howTo}</small></p></>}
        {data.ai_status.configured && !ai && (
          <div className="no-print">
            <label className="check"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); store.set('cs-ai-consent', e.target.checked ? '1' : '0'); setAuto(e.target.checked); store.set('cs-ai-auto', e.target.checked ? '1' : '0') }} />
              <span>{r.ai.consent(data.ai_status.sends_to ?? '')}</span></label>
            <label className="check"><input type="checkbox" checked={auto} disabled={!consent} onChange={(e) => { setAuto(e.target.checked); store.set('cs-ai-auto', e.target.checked ? '1' : '0') }} />
              <span>{r.ai.auto}</span></label>
            <button type="button" className="button primary" disabled={!consent || aiBusy} onClick={() => askAi(false)}>{aiBusy ? r.ai.writing : r.ai.write}</button>
          </div>
        )}
        {aiError && <p className="notice warn" role="alert">{aiError}</p>}
        {ai && (
          <div data-testid="rp-ai-text">
            <p className="plain">{ai.summary}</p>
            {ai.what_happened.length > 0 && <><h4>{r.ai.happened}</h4><ul>{ai.what_happened.map((w, i) => (
              <li key={i}>{w.at !== null && <button type="button" className="link-time" onClick={() => seek(w.at!)}>{fmtCall(w.at)}</button>} {w.text}</li>))}</ul></>}
            {ai.why_risky.length > 0 && <><h4>{r.ai.why}</h4><ul>{ai.why_risky.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
            {ai.advice.length > 0 && <><h4>{r.ai.advice}</h4><ul>{ai.advice.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
            {ai.quotes.length > 0 && <><h4>{r.ai.quotes}</h4><p>{ai.quotes.map((x, i) => <button key={i} type="button" className="chip" onClick={() => seekToQuote(x)}>“{x}”</button>)}</p></>}
            <p className="mut"><small>{r.ai.by(ai.model)}. {ai.attempts && ai.attempts.length > 1 ? `${r.ai.fellBack(ai.attempts.length - 1)} ` : ''}{r.ai.warn}</small></p>
            <button type="button" className="button small no-print" disabled={aiBusy} onClick={() => askAi(true)}>{aiBusy ? r.ai.writing : r.ai.again}</button>
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="rp-tl">
        <h3 id="rp-tl">{r.timelineTitle}</h3>
        <p className="mut"><small>{r.chartHelp}</small></p>
        <RiskChart duration={dur} risk={session.risk} events={shown} cursor={cursor} label={r.chartTitle} onSeek={seek} onPick={pick}
                   describe={(e) => describe(e, r, t).text} />
        <div className="toolbar no-print">
          <button type="button" className="button small primary" data-testid="rp-play"
                  onClick={() => { if (playing) setPlaying(false); else { if (cursor === null || cursor >= dur) setCursor(0); setPlaying(true) } }}>{playing ? r.pause : r.replay}</button>
          <button type="button" className="button small" onClick={() => { setPlaying(false); setCursor(0) }}>{r.restart}</button>
          <label className="field compact"><span className="visually-hidden">{r.speed}</span>
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label={r.speed}>{[1, 2, 4, 8].map((s) => <option key={s} value={s}>{s}×</option>)}</select></label>
          <button type="button" className="button small" onClick={() => { setPlaying(false); setCursor(null) }} disabled={cursor === null}>{r.showAll}</button>
          {cursor !== null && <span className="mut" data-testid="rp-cursor">{r.cursorAt(fmtCall(cursor))}</span>}
        </div>

        <div className="rp-filters no-print" role="group" aria-label={r.filtersTitle}>
          {SOURCES.filter((s) => allEvents.some((e) => e.source === s)).map((s) => (
            <button key={s} type="button" className={`chip${filters.sources.has(s) ? ' on' : ''}`} aria-pressed={filters.sources.has(s)} onClick={() => toggleSource(s)}>{r.sources[s]}</button>))}
          <select value={filters.category ?? ''} aria-label={r.filtersTitle} onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || null }))}>
            <option value="">{r.allTactics}</option>{categories.map((c) => <option key={c} value={c}>{categoryText(t, c).label}</option>)}</select>
          <input type="search" value={filters.query} placeholder={r.searchPlaceholder} aria-label={r.searchLabel} onChange={(e) => setFilters((f) => ({ ...f, query: e.target.value }))} />
        </div>

        <div className="rp-pair">
          <div>
            <h4>{r.eventsTitle}</h4>
            {shown.length === 0 ? <p className="mut">{r.noEvents}</p> : (
              <ol className="rp-events" data-testid="rp-events">
                {shown.map((e, i) => {
                  const d = describe(e, r, t)
                  return (
                    <li key={e.i} className={`${i === cur ? 'now' : ''}${cursor !== null && e.t > cursor ? ' future' : ''}`} aria-current={i === cur ? 'true' : undefined}
                        style={{ ['--i' as string]: Math.min(i, 14) } as React.CSSProperties}>
                      <button type="button" onClick={() => pick(e)}>
                        <span className="rp-time"><strong>{fmtCall(e.t)}</strong><small>{fmtClock(e.wall)}</small></span>
                        <span className={`tag src-${e.source}`}>{r.sources[e.source]}</span>
                        <span className="rp-what">{d.text}{d.quote && <q>{d.quote}</q>}</span>
                      </button>
                    </li>
                  )
                })}
              </ol>
            )}
            <p className="mut"><small>{r.callTime} · {r.clockTime}. {r.timesNote}</small></p>
          </div>
          <div>
            <h4>{r.transcriptTitle}</h4>
            {tracks.length > 1 && <label className="field compact"><span className="visually-hidden">{r.track}</span>
              <select value={mainTrack ?? ''} onChange={(e) => setTrack(e.target.value)} aria-label={r.track}>{tracks.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>}
            <div className="rp-transcript" ref={transcriptRef} data-testid="rp-transcript">
              {segments.length === 0 && <p className="mut">{r.noTranscript}</p>}
              {segments.map((s, i) => (
                <p key={i} data-seg={i} className={`${i === currentSeg ? 'now' : ''}${cursor !== null && s.first_t > cursor ? ' future' : ''}`}>
                  <button type="button" className="link-time" onClick={() => seek(s.first_t)}>{fmtCall(s.first_t)}</button>{' '}
                  {markQuotes(s.text, quotesByTrack).map((p, k) => (p.hit ? <mark key={k} className="mark">{p.text}</mark> : <span key={k}>{p.text}</span>))}
                </p>
              ))}
            </div>
            <p className="mut"><small>{r.maskedNote}</small></p>
          </div>
        </div>
      </section>
    </article>
  )
}
