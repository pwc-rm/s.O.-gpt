import { defineConfig, devices } from '@playwright/test';

// Two-phase approach (per the tutorial): AI writes these tests once, Playwright
// runs them natively — deterministic, repeatable, zero token cost at runtime.
//
// The cockpit runs locally in its in-memory fallback (no Cosmos / no OpenAI):
// marketplace, dashboards, detail edit+save and navigation are fully testable.
// The real LLM chat can't stream without an OpenAI key, so the chat spec asserts
// the SSE pipeline responds (token OR "not configured" error) — still end-to-end.
//
// Serial (workers: 1) on purpose: the in-memory backend is shared state, so a
// mutating test (detail save) must not race read-only ones.
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8100',
    trace: 'on-first-retry',
  },
  webServer: {
    command: '.venv/bin/uvicorn main:app --port 8100 --log-level warning',
    url: 'http://127.0.0.1:8100/health',
    reuseExistingServer: true,
    timeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
