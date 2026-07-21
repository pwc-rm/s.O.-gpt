import { test, expect } from '@playwright/test';

// Agent chat (s.O GPT design). Locally there is no OpenAI key, so we can't assert
// a real answer — but we CAN assert the agent-scoped UI renders and that the SSE
// chat endpoint responds end-to-end (a token, or the "not configured" error).
test.describe('Agent chat', () => {
  test('chat page is scoped to the agent (name + its starter questions)', async ({ page }) => {
    await page.goto('/agent/hr-vacation-assistant/chat');
    await expect(page.locator('#welcome-name')).toHaveText('HR Urlaubsassistent');
    await expect(page.locator('#suggestions button')).toHaveCount(3);
    await expect(page.locator('#input')).toBeVisible();
  });

  test('back link returns to the cockpit', async ({ page }) => {
    await page.goto('/agent/hr-vacation-assistant/chat');
    await expect(page.locator('#to-cockpit')).toHaveAttribute('href', '/');
  });

  test('sending a message drives the SSE chat pipeline end-to-end', async ({ page }) => {
    await page.goto('/agent/hr-vacation-assistant/chat');
    await page.locator('#input').fill('Wie viele Urlaubstage habe ich?');
    await page.getByRole('button', { name: 'SENDEN' }).click();
    // A user bubble appears immediately; the assistant bubble resolves to either a
    // streamed token or the configured "no OpenAI" error — both prove the pipeline.
    await expect(page.locator('#messages')).toContainText('Wie viele Urlaubstage habe ich?');
    await expect(page.locator('#messages .bubble').last()).not.toBeEmpty({ timeout: 20_000 });
  });
});
