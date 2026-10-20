import { useEffect, useRef, useState } from 'react'
import { topEvidence } from '../alert/AlertOverlay'
import { highlightKey } from './focus'
import { categoryText, type Dict } from '../i18n'
import { splitTranscript } from '../highlight'
import type { LiveState } from '../live/state'
import type { SpeakResult } from '../alert/alertDeps'
import { formatClock } from './derive'

export interface Focus { category: string; quote: string }

interface Props {
  t: Dict
  state: LiveState
  elapsed: number
  listening: boolean
  /** the warning covers the phone screen */
  takeover: boolean
  /** show the small amber strip */
  strip: boolean
  voice: SpeakResult | null
  focus: Focus | null
  onToggleListen: () => void
  onEnd: () => void
  onDismiss: () => void
  onRepeat: () => void
}

const nowClock = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })

/** A phone call screen as the protected person would see it: caller card, live captions with the risky words lit, risk strip. */
export default function PhoneSim({ t, state, elapsed, listening, takeover, strip, voice, focus, onToggleListen, onEnd, onDismiss, onRepeat }: Props) {
  const c = t.console
  const [clock, setClock] = useState(nowClock)
  useEffect(() => { const id = window.setInterval(() => setClock(nowClock()), 30_000); return () => window.clearInterval(id) }, [])
  const box = useRef<HTMLDivElement>(null)
  const ended = state.status === 'ended'
  const sub = state.status === 'reconnecting' ? c.reconnectingPhone : ended ? c.callEnded : formatClock(elapsed)

  // keep the newest words in view, unless a timeline item is selected: then bring those words into view
  useEffect(() => {
    const el = box.current
    if (!el) return
    const hit = focus ? el.querySelector<HTMLElement>('mark.focus') : null
    if (hit && typeof hit.scrollIntoView === 'function') hit.scrollIntoView({ block: 'center', behavior: 'smooth' })
    else el.scrollTop = el.scrollHeight
  }, [state.tracks, focus])

  const evidence = topEvidence(state.hits, 2)
  return (
    <div className="phone" data-testid="phone">
      <div className="phone-screen">
        <div className="phone-status" aria-hidden="true"><span>{clock}</span><span>▂▄▆ 5G</span></div>
        <div className={`phone-risk ${state.level}`} aria-hidden="true" data-testid="phone-risk"><span>{t.levels[state.level]}</span></div>
        {strip && <p className="phone-strip" role="status" data-testid="phone-strip">{c.phoneElevated}</p>}
        <div className="phone-caller">
          <div className="phone-avatar" aria-hidden="true">?</div>
          <div className="phone-name">{c.unknownCaller}</div>
          <div className="phone-number">{c.unknownNumber}</div>
          <div className="phone-time" data-testid="phone-time">{sub}</div>
        </div>
        <div className="phone-captions" ref={box} aria-label={c.captionsTitle} data-testid="phone-captions">
          {state.tracks.length === 0 ? <p className="phone-wait">{c.captionsWaiting}</p> : state.tracks.map((tr) => (
            <p key={tr.code} className="phone-line">
              {state.tracks.length > 1 && <small className="phone-lang">{tr.code} </small>}
              {splitTranscript(tr.text, tr.hits).map((seg, i) => seg.hit
                ? <mark key={i} className={`mark ${seg.hit.kind}${focus && highlightKey(seg.hit) === highlightKey(focus) ? ' focus' : ''}`}>{seg.text}</mark>
                : <span key={i}>{seg.text}</span>)}
            </p>
          ))}
        </div>
        <div className="phone-controls">
          <button type="button" className={`phone-btn${listening ? ' on' : ''}`} aria-pressed={listening} aria-label={c.speaker} onClick={onToggleListen} disabled={ended}>🔊</button>
          <button type="button" className="phone-btn end" aria-label={c.hangUp} onClick={onEnd} disabled={ended || state.status === 'stopping'}>📞</button>
        </div>
        {takeover && (
          <div className="phone-takeover" role="alert" data-testid="phone-takeover">
            <p className="ax-icon" aria-hidden="true">⚠</p>
            <h3>{t.alert.headline}</h3>
            <p>{t.alert.subline}</p>
            <ul>{t.advice.high.slice(0, 2).map((a, i) => <li key={i}>{a}</li>)}</ul>
            {evidence.length > 0 && (
              <ul className="phone-evidence">{evidence.map((h, i) => <li key={i}>“{h.quote}” <span>{categoryText(t, h.category).label}</span></li>)}</ul>
            )}
            {voice === 'unavailable' && <p className="ax-note" role="note">{t.alert.noVoice}</p>}
            <div className="ax-actions">
              <button type="button" className="ax-button primary" autoFocus onClick={onDismiss}>{t.alert.dismiss}</button>
              <button type="button" className="ax-button" onClick={onRepeat}>{t.alert.repeat}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
