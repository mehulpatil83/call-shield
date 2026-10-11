import { STRINGS, categoryText } from './i18n'

const KNOWN_CATEGORIES = [
  'otp_request', 'credential_request', 'payment_request', 'remote_access', 'urgency', 'threat', 'secrecy',
  'verification_bypass', 'authority', 'kyc_pretext', 'warning_otp', 'warning_cred',
]

describe('translations', () => {
  it('have the same list lengths in every language', () => {
    for (const lang of ['hi', 'mr'] as const) {
      expect(STRINGS[lang].limits).toHaveLength(STRINGS.en.limits.length)
      for (const level of ['high', 'elevated', 'low'] as const) {
        expect(STRINGS[lang].advice[level]).toHaveLength(STRINGS.en.advice[level].length)
      }
    }
  })
  it('cover every indicator category with non-empty text', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      for (const c of KNOWN_CATEGORIES) {
        const text = STRINGS[lang].categories[c]
        expect(text, `${lang}:${c}`).toBeDefined()
        expect(text.label.trim()).not.toBe('')
        expect(text.explain.trim()).not.toBe('')
      }
    }
  })
  it('keep the helpline numbers in the high-risk advice', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      expect(STRINGS[lang].advice.high.join(' ')).toContain('1930')
    }
  })
  it('format numbers in functions', () => {
    expect(STRINGS.mr.tooBig(25)).toContain('25')
    expect(STRINGS.hi.digitsCount(6)).toContain('6')
  })
  it('falls back for unknown categories', () => {
    expect(categoryText(STRINGS.en, 'new_thing', 'because').label).toBe('new thing')
  })
})
