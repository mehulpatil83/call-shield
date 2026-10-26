import '@testing-library/jest-dom/vitest'

// jsdom has no canvas: the WebGL decorations check for a context and quietly do nothing, so make the answer "none" without console noise
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext

// jsdom lacks these observers; the decorations only use them to resize and to pause off-screen, which tests do not need
class NoopObserver { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }
for (const name of ['ResizeObserver', 'IntersectionObserver']) {
  if (!(name in globalThis)) (globalThis as Record<string, unknown>)[name] = NoopObserver
}
