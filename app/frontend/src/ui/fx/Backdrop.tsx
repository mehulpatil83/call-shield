import { useCallback } from 'react'
import GradientASCII from './GradientASCII'
import { PALETTES } from './atmosphere'
import { useDarkScheme, useFps, useFpsWatchdog } from './effects'

/** The page background: a gradient made of letters that follows the risk of the call. Off, or quiet, on slow screens. */
export default function AppBackdrop() {
  const { mode, level, degrade } = useFps()
  const dark = useDarkScheme()
  const onSlow = useCallback(() => degrade(), [degrade])
  useFpsWatchdog(mode !== 'off', mode === 'full' ? 24 : 15, onSlow, mode)
  if (mode === 'off') return null
  const quiet = mode === 'reduced'
  const p = PALETTES[level]
  return (
    <div className="fx-backdrop" aria-hidden="true" data-testid="fx-backdrop" data-mode={mode} data-level={level}>
      <GradientASCII
        colors={p.colors} shape={p.shape} lightMode={!dark} cellSize={quiet ? 22 : 18} density={0.7}
        gradientOpacity={dark ? 0.5 : 0.6} glyphOpacity={0.55} glow={quiet ? 0 : 0.15} flicker={quiet ? 0 : 0.2} grain={0.05}
        speed={quiet ? 0 : p.speed} intro={!quiet} mouseInteraction={!quiet} clickEffect="none" scrambleRadius={0.12} dpr={1}
      />
    </div>
  )
}
