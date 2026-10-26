import GlitchLayer from '../ui/fx/GlitchLayer'
import { useEffect } from 'react'
import { categoryText, type Dict } from '../i18n'
import type { LiveState } from '../live/state'
import type { Hit } from '../types'
import type { SpeakResult } from './alertDeps'
import type { AlertSettings } from './useAlertExperience'

interface Props {
  t: Dict
  state: Pick<LiveState, 'level' | 'hits'>
  shown: 'none' | 'elevated' | 'high'
  settings: AlertSettings
  voice: SpeakResult | null
  onDismiss: () => void
  onRepeat: () => void
  onChange: (patch: Partial<AlertSettings>) => void
}

/** The strongest evidence first: requests, then pressure, then context; one per kind of tactic. Cautions are not evidence. */
export function topEvidence(hits: Hit[], n = 3): Hit[] {
  const rank: Record<string, number> = { request: 0, pressure: 1, context: 2 }
  const seen = new Set<string>()
  return [...hits].filter((h) => h.kind !== 'warning').sort((x, y) => rank[x.kind] - rank[y.kind])
    .filter((h) => (seen.has(h.category) ? false : (seen.add(h.category), true))).slice(0, n)
}

/** The three alert switches and the echo warning. */
export function AlertSettingsPanel({ t, settings, onChange, fullscreenLabel }: { t: Dict; settings: AlertSettings; onChange: (patch: Partial<AlertSettings>) => void; fullscreenLabel?: string }) {
  const a = t.alert
  return (
    <details className="ax-settings">
      <summary>{a.settings}</summary>
      <label className="check"><input type="checkbox" checked={settings.sound} onChange={(e) => onChange({ sound: e.target.checked })} /><span>{a.sound}</span></label>
      <label className="check"><input type="checkbox" checked={settings.voice} onChange={(e) => onChange({ voice: e.target.checked })} /><span>{a.voice}</span></label>
      <label className="check"><input type="checkbox" checked={settings.fullscreen} onChange={(e) => onChange({ fullscreen: e.target.checked })} /><span>{fullscreenLabel ?? a.fullscreen}</span></label>
      <p className="mut"><small>{a.echoNote}</small></p>
    </details>
  )
}

/** Full-screen red warning at high risk, an amber banner at elevated risk, and the alert settings. */
export default function AlertOverlay({ t, state, shown, settings, voice, onDismiss, onRepeat, onChange }: Props) {
  const a = t.alert
  const overlay = shown === 'high' && settings.fullscreen
  useEffect(() => {
    if (!overlay) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onDismiss() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [overlay, onDismiss])

  const evidence = topEvidence(state.hits)

  return (
    <>
      {overlay && (
        <div className="ax-overlay" role="alertdialog" aria-modal="true" aria-labelledby="ax-title" aria-describedby="ax-sub" data-testid="alert-overlay">
        <GlitchLayer tone="alert" strength={2} />
          <div className="ax-card">
            <p className="ax-icon" aria-hidden="true">⚠</p>
            <h2 id="ax-title">{a.headline}</h2>
            <p id="ax-sub" className="ax-sub">{a.subline}</p>
            <ul className="ax-advice">{t.advice[state.level === 'low' ? 'high' : state.level].slice(0, 3).map((line, i) => <li key={i}>{line}</li>)}</ul>
            {evidence.length > 0 && (
              <div className="ax-evidence">
                <p className="ax-label">{a.heard}</p>
                <ul>{evidence.map((h, i) => <li key={i}>“{h.quote}” <span>{categoryText(t, h.category).label}</span></li>)}</ul>
              </div>
            )}
            {voice === 'unavailable' && <p className="ax-note" role="note">{a.noVoice}</p>}
            <div className="ax-actions">
              <button type="button" className="ax-button primary" autoFocus onClick={onDismiss}>{a.dismiss}</button>
              {settings.voice && <button type="button" className="ax-button" onClick={onRepeat}>{a.repeat}</button>}
            </div>
          </div>
        </div>
      )}
      {!overlay && shown !== 'none' && (
        <div className={`ax-banner ${shown}`} role="status" data-testid="alert-banner">
          <span>{shown === 'high' ? a.headline + '. ' + a.subline : a.elevated}</span>
          <button type="button" className="ax-close" onClick={onDismiss} aria-label={a.dismiss}>×</button>
        </div>
      )}
      <AlertSettingsPanel t={t} settings={settings} onChange={onChange} />
    </>
  )
}
