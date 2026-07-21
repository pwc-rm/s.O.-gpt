import { test, expect } from '@playwright/test';

// FinOps / AgentOps / Settings dashboards render their KPIs and tables.
test.describe('Dashboards', () => {
  test('FinOps shows KPIs and a cost-per-agent table with all agents', async ({ page }) => {
    await page.goto('/');
    await page.locator('.navbtn[data-view="finops"]').click();
    await expect(page.getByText('Gesamtbudget (Monat)')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Kostenverlauf der letzten 30 Tage' })).toBeVisible();
    await expect(page.locator('#view-finops svg')).toBeVisible();
    await expect(page.getByText('Gesamtausgaben (30 Tage)')).toBeVisible();
    await expect(page.getByText('Budget-Auslastung')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Kosten pro Agent' })).toBeVisible();
    await expect(page.locator('#view-finops table tbody tr')).toHaveCount(5);
  });

  test('AgentOps shows alerts and a performance table', async ({ page }) => {
    await page.goto('/');
    await page.locator('.navbtn[data-view="agentops"]').click();
    await expect(page.getByRole('heading', { name: 'Alerts & Exceptions' })).toBeVisible();
    await expect(page.getByText('API Timeout: Sales Forecasting')).toBeVisible();
    await expect(page.locator('#view-agentops table tbody tr')).toHaveCount(5);
  });

  test('Settings shows profile, API keys and organisation', async ({ page }) => {
    await page.goto('/');
    await page.locator('.navbtn[data-view="settings"]').click();
    await expect(page.getByRole('heading', { name: 'Benutzerprofil' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'API & Governance' })).toBeVisible();
    await expect(page.getByText('Marketing Agent Prod')).toBeVisible();
    // The e-mail is shown in a disabled input (IdP-provided) — assert its value.
    await expect(page.locator('#view-settings input:disabled')).toHaveValue('max.mustermann@s-oliver.de');
  });
});
