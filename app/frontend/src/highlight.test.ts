import { splitTranscript } from './highlight'
import type { Hit } from './types'

const hit = (start: number, end: number, category = 'urgency'): Hit => ({
  category, kind: 'pressure', quote: '', start, end, explanation: '', source: '',
})

describe('splitTranscript', () => {
  it('joins back into the original text', () => {
    const text = 'please share the otp right now ok'
    const segs = splitTranscript(text, [hit(7, 20, 'otp_request'), hit(21, 30)])
    expect(segs.map((s) => s.text).join('')).toBe(text)
    expect(segs.filter((s) => s.hit).map((s) => s.text)).toEqual(['share the otp', 'right now'])
  })
  it('skips overlapping and out-of-range hits', () => {
    const text = 'abcdefghij'
    const segs = splitTranscript(text, [hit(2, 6), hit(4, 8), hit(8, 99), hit(-1, 3)])
    expect(segs.map((s) => s.text).join('')).toBe(text)
    expect(segs.filter((s) => s.hit)).toHaveLength(1)
  })
  it('handles Devanagari and empty input', () => {
    const text = 'ओटीपी मला सांगा'
    const segs = splitTranscript(text, [hit(0, 5)])
    expect(segs[0].text).toBe('ओटीपी')
    expect(splitTranscript('', [])).toEqual([])
  })
})
