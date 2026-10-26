import type { Lang } from '../../types'
import { useFx, type FxMode } from './effects'
import { FXTEXT } from './text'

/** A small switch in the header: Full / Reduced / Off. */
export default function EffectsControl({ lang }: { lang: Lang }) {
  const { mode, setMode, autoReduced } = useFx()
  const x = FXTEXT[lang]
  return (
    <label className="field compact fx-control">
      <span className="visually-hidden">{x.label}</span>
      <select aria-label={x.label} value={mode} onChange={(e) => setMode(e.target.value as FxMode)}>
        <option value="full">{x.label}: {x.full}</option>
        <option value="reduced">{x.label}: {x.reduced}</option>
        <option value="off">{x.label}: {x.off}</option>
      </select>
      {autoReduced && <small className="mut fx-note" role="status">{x.auto}</small>}
    </label>
  )
}
