import { test, expect } from '@playwright/test';

// Marketplace: agents grouped by category, each card shows its SOURCE
// (Auto-Discovery origin) — the feature explicitly requested.
test.describe('Marketplace & sources', () => {
  test('agents are grouped by the three categories', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'HR & People' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'IT & Infrastructure' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Sales & Marketing' })).toBeVisible();
  });

  test('every source origin is shown on the dashboard', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Azure AI Foundry').first()).toBeVisible();
    await expect(page.getByText('Amazon Bedrock').first()).toBeVisible();
    await expect(page.getByText('Custom / In-House').first()).toBeVisible();
  });

  test('each agent card carries a source badge', async ({ page }) => {
    await page.goto('/');
    const badges = page.locator('[title="Quelle / Auto-Discovery"]');
    await expect(badges).toHaveCount(5);
  });

  test('each agent card shows a thumbs-up rating badge', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[title$="Bewertungen"]')).toHaveCount(5);
  });

  test('status pills (Aktiv / Inaktiv) are rendered', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Aktiv', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Inaktiv', { exact: true }).first()).toBeVisible();
  });

  test('category filter narrows the list', async ({ page }) => {
    await page.goto('/');
    await page.locator('#cat-filter').selectOption('IT & Infrastructure');
    await expect(page.getByText('IT Support Bot Level 1')).toBeVisible();
    await expect(page.getByText('HR Urlaubsassistent')).toHaveCount(0);
  });
});
