import LetterGlitch from './LetterGlitch'
import { GLITCH, type GlitchTone } from './atmosphere'
import { useDarkScheme, useFx } from './effects'

interface Props { tone?: GlitchTone; /** how loud: 1 is a header strip, 2 is an alarm */ strength?: number; interactive?: boolean }

/** Glitching letters as a background for a panel (put it first inside a `position: relative` panel; its content stays above). */
export default function GlitchLayer({ tone = 'low', strength = 1, interactive = true }: Props) {
  const { mode } = useFx()
  const dark = useDarkScheme()
  if (mode === 'off') return null
  const quiet = mode === 'reduced'
  const c = GLITCH[tone][tone === 'alert' || dark ? 'dark' : 'light']
  return (
    <div className="fx-layer" aria-hidden="true" data-testid="fx-glitch" data-tone={tone}>
      <LetterGlitch
        glitchColors={c.colors} baseColor={c.base} fontSize={12} spacing={0.5} density={0.85} baseOpacity={dark || tone === 'alert' ? 0.12 * strength : 0.1}
        glitchAmount={quiet ? 0.12 : 0.3 * strength} speed={quiet ? 0.25 : 0.7 * strength} flow={quiet ? 0.1 : 0.4} smooth interactive={interactive && !quiet}
        cursorRadius={90} clickEffect="none" edgeFade={0.04} centerFade={tone === 'alert' ? 0.5 : 0.35} intro={!quiet} dpr={1} lightMode={!dark && tone !== 'alert'}
      />
    </div>
  )
}
