import { test, expect } from '@playwright/test';

// Core user journey that must always work: open cockpit → see agents →
// open an agent's management → start an agent → land in the agent chat.
test.describe('Happy path', () => {
  test('cockpit loads with the agent marketplace', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#header-title')).toHaveText('Agent Marketplace');
    await expect(page.getByText('HR Urlaubsassistent')).toBeVisible();
  });

  test('all five demo agents are listed', async ({ page }) => {
    await page.goto('/');
    for (const name of [
      'HR Urlaubsassistent', 'Recruiting Screener', 'IT Support Bot Level 1',
      'Sales Forecasting', 'Social Media Copywriter',
    ]) {
      await expect(page.getByText(name, { exact: true })).toBeVisible();
    }
  });

  test('"Verwalten" opens the agent detail view', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Verwalten' }).first().click();
    await expect(page.locator('#header-title')).toHaveText('Agent verwalten');
    await expect(page.getByText('Allgemeine Informationen')).toBeVisible();
  });

  test('"Agent starten" navigates to the agent chat', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Agent starten' }).first().click();
    await expect(page).toHaveURL(/\/agent\/.+\/chat/);
    await expect(page.locator('#agent-name-top')).not.toHaveText('Agent');
  });
});
