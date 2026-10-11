import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// `npm run dev` proxies /api to the Python backend (python -m app.run --no-browser)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/setupTests.ts'] },
})
