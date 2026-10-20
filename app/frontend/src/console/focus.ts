/** A flagged phrase is identified by its tactic and the exact words, so a timeline item can find the same words in the captions. */
export const highlightKey = (h: { category: string; quote: string }): string => `${h.category}\u0000${h.quote.toLowerCase()}`
