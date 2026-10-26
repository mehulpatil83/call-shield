import type { Level } from '../../types'
import type { GradientASCIIShape } from './GradientASCII'

/** The page background changes with the risk of the call: calm blue, amber, then red. Edit here to tune the look. */
export const PALETTES: Record<Level, { colors: string[]; shape: GradientASCIIShape; speed: number }> = {
  low: { colors: ['#1e3fd8', '#f6f8ff', '#a5d8ff', '#38bdf8'], shape: 'horizon', speed: 0.5 },
  elevated: { colors: ['#92400e', '#fff7ed', '#fcd34d', '#f59e0b'], shape: 'rise', speed: 0.8 },
  high: { colors: ['#7f1d1d', '#fff1f2', '#fca5a5', '#ef4444'], shape: 'eclipse', speed: 1.1 },
}

export type GlitchTone = Level | 'alert'

/** Colours of the glitching letters, per tone and per colour scheme. */
export const GLITCH: Record<GlitchTone, { dark: { colors: string[]; base: string }; light: { colors: string[]; base: string } }> = {
  low: { dark: { colors: ['#9db4ff', '#e6edff'], base: '#8fa0c4' }, light: { colors: ['#1d4ed8', '#0f172a'], base: '#1f2937' } },
  elevated: { dark: { colors: ['#fcd34d', '#fff4d1'], base: '#c9a86a' }, light: { colors: ['#b45309', '#78350f'], base: '#4b3b1f' } },
  high: { dark: { colors: ['#ff9a9a', '#ffe3e3'], base: '#d38a8a' }, light: { colors: ['#b91c1c', '#7f1d1d'], base: '#3b1f1f' } },
  alert: { dark: { colors: ['#ffffff', '#ffd0d0'], base: '#ffd6d6' }, light: { colors: ['#ffffff', '#ffd0d0'], base: '#ffd6d6' } },
}

/** The phone's foil: a different holographic pattern and metal for each level. */
export const PHONE_LOOK: Record<Level, { preset: 'swirl' | 'gold' | 'shards'; foil: string; intensity: number }> = {
  low: { preset: 'swirl', foil: '#cfd6e6', intensity: 0.7 },
  elevated: { preset: 'gold', foil: '#e8d3a2', intensity: 0.85 },
  high: { preset: 'shards', foil: '#f0b4b4', intensity: 0.95 },
}
