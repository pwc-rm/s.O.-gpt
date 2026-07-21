import { test, expect } from '@playwright/test';

// Sidebar navigation switches views and updates the header title.
test.describe('Navigation', () => {
  test('sidebar switches between all four views', async ({ page }) => {
    await page.goto('/');
    await page.locator('.navbtn[data-view="finops"]').click();
    await expect(page.locator('#header-title')).toHaveText('FinOps & Kostenkontrolle');

    await page.locator('.navbtn[data-view="agentops"]').click();
    await expect(page.locator('#header-title')).toHaveText('AgentOps & Performance');

    await page.locator('.navbtn[data-view="settings"]').click();
    await expect(page.locator('#header-title')).toHaveText('Einstellungen');

    await page.locator('.navbtn[data-view="marketplace"]').click();
    await expect(page.locator('#header-title')).toHaveText('Agent Marketplace');
  });

  test('"Zurück zu s.O GPT" links back to the s.O GPT', async ({ page }) => {
    await page.goto('/');
    const href = await page.locator('#back-sogpt').getAttribute('href');
    expect(href).toContain('so-gpt-showcase-backend');
  });
});
