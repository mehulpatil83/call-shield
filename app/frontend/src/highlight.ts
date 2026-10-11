import type { Hit } from './types'

export interface Segment { text: string; hit: Hit | null; index: number | null }

/** Split a transcript into plain and highlighted pieces. Overlapping hits are skipped, so every
 * character appears exactly once and the pieces always join back into the original text. */
export function splitTranscript(text: string, hits: Hit[]): Segment[] {
  const sorted = hits
    .map((h, i) => ({ h, i }))
    .filter(({ h }) => h.start >= 0 && h.end > h.start && h.end <= text.length)
    .sort((a, b) => a.h.start - b.h.start || b.h.end - a.h.end)
  const out: Segment[] = []
  let pos = 0
  for (const { h, i } of sorted) {
    if (h.start < pos) continue
    if (h.start > pos) out.push({ text: text.slice(pos, h.start), hit: null, index: null })
    out.push({ text: text.slice(h.start, h.end), hit: h, index: i })
    pos = h.end
  }
  if (pos < text.length) out.push({ text: text.slice(pos), hit: null, index: null })
  return out
}
