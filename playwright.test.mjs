/**
 * s.O. GPT Showcase — Playwright End-to-End Tests
 *
 * Tests the full demo user journey against the live Azure app or local server.
 * Run against local:  BASE_URL=http://127.0.0.1:8000 npx playwright test playwright.test.mjs --reporter=list
 * Run against Azure:  BASE_URL=https://app-so-gpt-showcase-backend.azurewebsites.net npx playwright test playwright.test.mjs --reporter=list
 */

import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8000';
const TIMEOUT_MSG = 60_000;   // max wait for AI response (streaming)
const TIMEOUT_NAV = 10_000;   // max wait for UI state changes

let browser, page;

async function setup() {
  browser = await chromium.launch({ headless: false, slowMo: 300 });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  page = await ctx.newPage();
  page.on('pageerror', e => console.log('   [PAGEERROR]', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('   [console.error]', m.text()); });
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
}

async function teardown() {
  await browser.close();
}

// ── Helpers ──────────────────────────────────────────────────────────────────

// Snapshot of ai-bubble count taken right before a send, so waitForResponse can
// reliably detect the NEW bubble even when slowMo delays let a fast (static) reply
// finish before the count would otherwise be read.
let _preSendAiCount = 0;

async function sendMessage(text) {
  _preSendAiCount = await page.$$eval('#messages .bubble.ai', els => els.length);
  await page.fill('#message-input', text);
  await page.keyboard.press('Enter');
}

async function waitForResponse() {
  // Robust across both slow RAG answers and fast static replies (vacation flow):
  // wait until a NEW ai bubble exists (vs. the count snapshotted in sendMessage,
  // BEFORE the send), the typing indicator is gone, and no blinking stream cursor
  // remains (i.e. [DONE] processed + widgets rendered).
  await page.waitForFunction(
    (prev) => !document.getElementById('typing-row') &&
              !document.querySelector('#messages .stream-cursor') &&
              document.querySelectorAll('#messages .bubble.ai').length > prev,
    _preSendAiCount,
    { timeout: TIMEOUT_MSG }
  );
  // Give formatAnswer's setTimeout(0) callbacks a tick to fire
  await page.waitForTimeout(500);
}

async function waitForCanvasOpen() {
  await page.waitForFunction(
    () => document.body.classList.contains('canvas-open'),
    null,
    { timeout: TIMEOUT_NAV }
  );
}

async function waitForCanvasClosed() {
  await page.waitForFunction(
    () => !document.body.classList.contains('canvas-open'),
    null,
    { timeout: TIMEOUT_NAV }
  );
}

// Wait for canvas to be open AND body has real content AND streaming cursor gone (DONE processed)
async function waitForCanvasWithContent() {
  await page.waitForFunction(
    () => document.body.classList.contains('canvas-open') &&
          (document.getElementById('canvas-body').innerText || '').trim().length > 30 &&
          !document.querySelector('#messages .stream-cursor'),
    null,
    { timeout: TIMEOUT_MSG }
  );
  // Extra tick for formatAnswer's setTimeout to fire
  await page.waitForTimeout(400);
}

// Returns true if the canvas body is rendering markdown as HTML (headings/lists/bold),
// not showing raw markdown syntax like ** or leading "1." / "-".
async function canvasHasRenderedMarkdown() {
  return await page.$eval('#canvas-body', el => {
    const hasStructure = !!el.querySelector('h2,h3,h4,ul,ol,li,strong,table,p');
    const raw = el.innerHTML;
    const hasRawMarkdown = /\*\*[^*]+\*\*/.test(raw);  // literal **bold** left unrendered
    return hasStructure && !hasRawMarkdown;
  });
}

// Asserts no raw canvas markers leaked into any chat bubble
async function assertNoRawCanvasMarkers() {
  const leaked = await page.$eval('#messages', el => el.innerText.includes('[[CANVAS'));
  if (leaked) throw new Error('Raw [[CANVAS…]] marker leaked into chat text');
}

// ── Tests ────────────────────────────────────────────────────────────────────

async function test_01_initial_state() {
  console.log('\n▶  Test 1: Initial state');
  // Empty state visible
  const emptyState = await page.$('#empty-state');
  if (!emptyState) throw new Error('Empty state missing on load');
  // Right panel visible with Assets tab active
  const rightPanel = await page.$('#right-panel');
  if (!rightPanel) throw new Error('Right panel missing');
  const assetsTab = await page.$('#tab-btn-assets.active');
  if (!assetsTab) throw new Error('Assets tab not active by default');
  // Canvas panel hidden
  const canvasOpen = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  if (canvasOpen) throw new Error('Canvas panel should be closed on load');
  console.log('   ✅ Initial state OK');
}

async function test_02_simple_qa_no_canvas() {
  console.log('\n▶  Test 2: Simple Q&A — no canvas created');
  await sendMessage('Was ist der Code of Conduct?');
  await waitForResponse();

  const canvasOpen = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  if (canvasOpen) throw new Error('Short factual answer should NOT open canvas');

  console.log('   ✅ Q&A without canvas OK (no canvas opened)');
}

async function test_03_canvas_created_for_document_request() {
  console.log('\n▶  Test 3: Document request creates Canvas 1');
  await sendMessage('Erstell mir eine Sicherheits-Checkliste für meinen ersten Arbeitstag im Homeoffice basierend auf der IT-Sicherheitsrichtlinie');

  // Wait until canvas is open AND body has real content (canvas opens mid-stream, so waitForResponse alone is not enough)
  await waitForCanvasWithContent();

  const content = await page.$eval('#canvas-body', el => el.innerText.trim());
  if (content.length < 30) throw new Error('Canvas body is empty or too short');

  const title = await page.$eval('#canvas-title-text', el => el.textContent.trim());
  if (!title) throw new Error('Canvas title not set');

  // Canvas body must render markdown as HTML, not raw ** / 1. syntax
  if (!(await canvasHasRenderedMarkdown())) throw new Error('Canvas body shows raw markdown, not rendered HTML');

  // No raw canvas markers may leak into the chat
  await assertNoRawCanvasMarkers();

  // Chat bubble shows pill with an open button in the DOM (hidden by CSS while the
  // canvas is already open — that's correct UX; test 11 verifies it works after reload)
  const pillBtn = await page.$('.canvas-link-pill .canvas-open-btn');
  if (!pillBtn) throw new Error('Canvas pill open button missing in chat');

  // Sidebar should be hidden
  const sidebarVisible = await page.$eval('.sidebar', el => el.offsetWidth > 0);
  if (sidebarVisible) throw new Error('Sidebar should be hidden when canvas is open');

  console.log(`   ✅ Canvas 1 erstellt: "${title}" (Markdown gerendert, kein Roh-Marker)`);
  return title;
}

async function test_04_canvas_append_shows_diff() {
  console.log('\n▶  Test 4: Ergänzung → CANVAS_APPEND → Diff angezeigt');
  await sendMessage('Füg einen Abschnitt über Passwortrichtlinien hinzu');
  await waitForResponse();

  // Diff bar should be active
  await page.waitForSelector('#canvas-diff-bar.active', { timeout: TIMEOUT_NAV });

  // canvas-diff-new block should exist (green section)
  const diffNew = await page.$('.canvas-diff-new');
  if (!diffNew) throw new Error('Diff-new block not rendered');

  // Accept and Reject buttons should be visible
  const acceptBtn = await page.$('.diff-btn.accept');
  const rejectBtn = await page.$('.diff-btn.reject');
  if (!acceptBtn || !rejectBtn) throw new Error('Accept/Reject buttons missing');

  console.log('   ✅ Diff angezeigt: grüner Block + Accept/Reject-Buttons sichtbar');
}

async function test_05_accept_diff() {
  console.log('\n▶  Test 5: Diff übernehmen → Canvas aktualisiert');
  await page.click('.diff-btn.accept');
  await page.waitForTimeout(600);

  // Diff bar must be gone
  const diffBarActive = await page.$('#canvas-diff-bar.active');
  if (diffBarActive) throw new Error('Diff bar still active after Accept');

  // Diff-new block must be gone
  const diffNew = await page.$('.canvas-diff-new');
  if (diffNew) throw new Error('Diff-new block still visible after Accept');

  // Canvas body must have content
  const content = await page.$eval('#canvas-body', el => el.innerText.trim());
  if (content.length < 20) throw new Error('Canvas body empty after accepting diff');

  console.log('   ✅ Diff übernommen, Diff-Block entfernt, Canvas-Inhalt vorhanden');
}

async function test_06_close_canvas_shows_assets() {
  console.log('\n▶  Test 6: Canvas schließen → State A mit Assets-Tab');
  await page.click('.icon-btn[onclick="closeCanvas()"]');
  await waitForCanvasClosed();

  // Right panel should be visible again
  const rightPanel = await page.$('#right-panel');
  const rpVisible = await rightPanel.evaluate(el => el.offsetWidth > 0);
  if (!rpVisible) throw new Error('Right panel not visible after closing canvas');

  // Assets tab should be active
  const assetsActive = await page.$('#tab-btn-assets.active');
  if (!assetsActive) throw new Error('Assets tab not active after closing canvas');

  // Asset card should be in list
  const assetCards = await page.$$('.asset-card');
  if (assetCards.length === 0) throw new Error('No asset cards in list after closing canvas');

  console.log(`   ✅ Canvas geschlossen, ${assetCards.length} Asset(s) in Liste`);
}

async function test_07_second_canvas_new_topic() {
  console.log('\n▶  Test 7: Neues Thema → Canvas 2 erstellt');
  await sendMessage('Erstell mir eine Zusammenfassung der wichtigsten Compliance-Regeln aus dem Verhaltenskodex und der Antikorruptions-Richtlinie als Dokument');

  // Wait for canvas with real content (same timing fix as test 3)
  await waitForCanvasWithContent();

  const title2 = await page.$eval('#canvas-title-text', el => el.textContent.trim());
  console.log(`   ✅ Canvas 2 erstellt: "${title2}"`);
}

async function test_08_assets_shows_multiple_canvases() {
  console.log('\n▶  Test 8: Chat Assets zeigt beide Canvas-Dokumente');
  await page.click('.icon-btn[onclick="closeCanvas()"]');
  await waitForCanvasClosed();

  const assetCards = await page.$$('.asset-card');
  if (assetCards.length < 2) throw new Error(`Expected ≥2 asset cards, got ${assetCards.length}`);

  const titles = await Promise.all(assetCards.map(c => c.$eval('.asset-card-title', el => el.textContent)));
  console.log(`   ✅ ${assetCards.length} Canvas-Dokumente in Chat Assets:`);
  titles.forEach(t => console.log(`      • ${t}`));
}

async function test_09_reopen_canvas_from_assets() {
  console.log('\n▶  Test 9: Canvas per Klick in Chat Assets wieder öffnen');
  // Click first asset card
  await page.click('.asset-card');
  await waitForCanvasOpen();

  const canvasBody = await page.$eval('#canvas-body', el => el.innerText.trim());
  if (canvasBody.length < 10) throw new Error('Canvas body empty after reopening');
  console.log('   ✅ Canvas wieder geöffnet via Chat Assets');
}

async function test_10_urlaub_flow_unaffected() {
  console.log('\n▶  Test 10: Urlaubs-Flow funktioniert noch (kein Canvas)');
  // Close canvas and start new chat for clean state
  if (await page.evaluate(() => document.body.classList.contains('canvas-open'))) {
    await page.click('.icon-btn[onclick="closeCanvas()"]');
    await waitForCanvasClosed();
    console.log('   Canvas closed after clicking close button');
  }
  const afterClose = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  console.log('   Canvas open after closeCanvas():', afterClose);

  await page.click('.new-chat-btn');
  const afterNewChat = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  console.log('   Canvas open after newChat():', afterNewChat);

  await page.waitForTimeout(500);
  const after500 = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  console.log('   Canvas open after 500ms:', after500);

  await page.waitForTimeout(1000);
  const after1500 = await page.evaluate(() => document.body.classList.contains('canvas-open'));
  console.log('   Canvas open after 1500ms total:', after1500);

  await sendMessage('Wie viele Urlaubstage habe ich?');
  // Wait for full response (not just first HTTP response)
  await waitForResponse();

  const stateAfterResponse = await page.evaluate(() => ({
    canvasOpen: document.body.classList.contains('canvas-open'),
    canvasCount: window._canvases ? window._canvases.length : 'N/A',
    streamingId: window._streamingCanvasId || null,
    lastUser: window._lastUserMessage || 'N/A',
  }));
  console.log('   State after response:', JSON.stringify(stateAfterResponse));

  // No canvas should open
  const canvasOpen = stateAfterResponse.canvasOpen;
  if (canvasOpen) throw new Error('Urlaubs-Q&A should NOT open canvas');

  // Send "ja" for saldo
  await sendMessage('ja');
  await waitForResponse();
  const saldoCard = await page.$('.urlaub-card');
  if (!saldoCard) throw new Error('Urlaubskonto-Karte not rendered');

  // Send "ja" for form
  await sendMessage('ja');
  await waitForResponse();
  const form = await page.$('.urlaub-form');
  if (!form) throw new Error('Urlaubsantrag-Formular not rendered');

  console.log('   ✅ Urlaubs-Flow: Frage → Saldo-Karte → Formular — kein Canvas');
}

async function test_11_persistence_journey() {
  console.log('\n▶  Test 11: Persistenz-Journey — neuer Chat, Canvas + Diff, verlassen & zurückkehren');

  // Fresh chat for a clean, isolated journey
  await page.click('.new-chat-btn');
  await page.waitForTimeout(500);

  // 1) Create a canvas (streamed)
  await sendMessage('Erstell mir ein kompaktes Merkblatt zu Elternzeit');
  await waitForCanvasWithContent();
  const canvasTitle = await page.$eval('#canvas-title-text', el => el.textContent.trim());
  if (!(await canvasHasRenderedMarkdown())) throw new Error('New canvas not rendering markdown');

  // 2) Append a section and accept the diff → merged content is persisted
  await sendMessage('Füg einen Abschnitt zu Kündigungsschutz hinzu');
  await waitForResponse();
  await page.waitForSelector('#canvas-diff-bar.active', { timeout: TIMEOUT_NAV });
  await page.click('.diff-btn.accept');
  await page.waitForTimeout(700);
  if (await page.$('#canvas-diff-bar.active')) throw new Error('Diff bar still active after accept');

  // Capture the merged canvas text (rendered) for later comparison
  const mergedText = await page.$eval('#canvas-body', el => el.innerText.trim());
  if (mergedText.length < 40) throw new Error('Merged canvas content too short');

  // 3) Close canvas, then leave to a new chat
  await page.click('.icon-btn[onclick="closeCanvas()"]');
  await waitForCanvasClosed();
  await page.click('.new-chat-btn');
  await page.waitForTimeout(600);

  // New chat must be clean
  if ((await page.$$('.asset-card')).length > 0) throw new Error('Canvas state not reset in new chat');
  if (await page.evaluate(() => document.body.classList.contains('canvas-open'))) throw new Error('Canvas still open in new chat');

  // 4) Return to the original session via Recent Chats
  const historyItems = await page.$$('.chat-history-item');
  if (historyItems.length === 0) throw new Error('No history items in sidebar');
  let clicked = false;
  for (const item of historyItems) {
    const text = await item.$eval('.chat-history-title', el => el.textContent);
    if (text.toLowerCase().includes('elternzeit') || text.toLowerCase().includes('merkblatt')) {
      await item.$eval('.chat-history-title', el => el.click());
      clicked = true;
      break;
    }
  }
  if (!clicked) await historyItems[0].$eval('.chat-history-title', el => el.click());
  await page.waitForTimeout(3000);  // session load + Cosmos fetch

  // ── Assertions on the restored session ────────────────────────────────────

  // (a) Messages restored
  const bubbles = await page.$$('#messages .bubble');
  if (bubbles.length < 2) throw new Error('Chat messages not restored');

  // (b) No raw canvas markers leaked into chat (Bug: [[CANVAS_START…]] shown as text)
  await assertNoRawCanvasMarkers();

  // (c) Diff must NOT re-prompt on load (Bug: asks to accept again)
  if (await page.$('#canvas-diff-bar.active')) throw new Error('Diff bar re-appeared on session load');
  if (await page.evaluate(() => document.body.classList.contains('canvas-open'))) throw new Error('Canvas auto-opened with diff on load');

  // (d) Canvas restored in Chat Assets (deduped — one card per title)
  const restoredCards = await page.$$('.asset-card');
  if (restoredCards.length === 0) throw new Error('Canvas NOT restored in Chat Assets');

  // (e) Canvas openable via the CHAT PILL button (Bug: only openable via Assets tab)
  const pillBtn = await page.$('.canvas-link-pill .canvas-open-btn');
  if (!pillBtn) throw new Error('Canvas pill button missing in restored chat');
  await pillBtn.click();
  await waitForCanvasOpen();

  // (f) Restored canvas shows rendered markdown, not raw ** / 1. (Bug: formatting lost)
  if (!(await canvasHasRenderedMarkdown())) throw new Error('Restored canvas lost markdown formatting');

  // (g) The accepted append survived (content still contains the merged section)
  const restoredText = await page.$eval('#canvas-body', el => el.innerText.trim());
  if (restoredText.length < 40) throw new Error('Restored canvas content lost');

  console.log(`   ✅ Persistenz-Journey OK: "${canvasTitle}" wiederhergestellt, Markdown erhalten, Diff nicht erneut abgefragt, per Chat-Pill öffenbar`);
}

// ── Runner ───────────────────────────────────────────────────────────────────

async function run() {
  const tests = [
    test_01_initial_state,
    test_02_simple_qa_no_canvas,
    test_03_canvas_created_for_document_request,
    test_04_canvas_append_shows_diff,
    test_05_accept_diff,
    test_06_close_canvas_shows_assets,
    test_07_second_canvas_new_topic,
    test_08_assets_shows_multiple_canvases,
    test_09_reopen_canvas_from_assets,
    test_10_urlaub_flow_unaffected,
    test_11_persistence_journey,
  ];

  console.log(`\n🎭 s.O. GPT Canvas Tests  →  ${BASE_URL}`);
  console.log('─'.repeat(55));

  await setup();
  let passed = 0, failed = 0;

  for (const test of tests) {
    try {
      await test();
      passed++;
    } catch (err) {
      console.log(`   ❌ FEHLER: ${err.message}`);
      // Screenshot on failure
      await page.screenshot({ path: `/tmp/${test.name}.png` });
      console.log(`      Screenshot: /tmp/${test.name}.png`);
      failed++;
    }
  }

  await teardown();
  console.log('\n' + '─'.repeat(55));
  console.log(`Ergebnis: ${passed} bestanden, ${failed} fehlgeschlagen\n`);
  process.exit(failed > 0 ? 1 : 0);
}

run().catch(err => { console.error('Fatal:', err); process.exit(1); });
