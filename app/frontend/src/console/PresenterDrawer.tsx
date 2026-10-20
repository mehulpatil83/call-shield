import { useState } from 'react'
import { DEMO_SCRIPTS } from '../demo/scripts'
import type { Dict } from '../i18n'

/** The acted scripts for the demo, ready to read aloud. */
export default function PresenterDrawer({ t }: { t: Dict }) {
  const c = t.console
  const [copied, setCopied] = useState<string | null>(null)
  const titles = { scam: c.scriptScam, scamShort: c.scriptScamShort, friendly: c.scriptFriendly, warning: c.scriptWarning }
  const copy = async (id: string, text: string) => {
    try { await navigator.clipboard.writeText(text); setCopied(id); window.setTimeout(() => setCopied((cur) => (cur === id ? null : cur)), 1500) } catch { /* clipboard not available */ }
  }
  return (
    <details className="presenter" data-testid="presenter">
      <summary>{c.presenterTitle}</summary>
      <p className="mut"><small>{c.presenterIntro}</small></p>
      {DEMO_SCRIPTS.map((s) => (
        <div key={s.id} className="script">
          <h5>{titles[s.id]}</h5>
          <p lang="en">{s.text}</p>
          <button type="button" className="button small" onClick={() => void copy(s.id, s.text)}>{copied === s.id ? c.copied : c.copy}</button>
        </div>
      ))}
    </details>
  )
}
