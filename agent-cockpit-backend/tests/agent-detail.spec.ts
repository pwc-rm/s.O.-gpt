import { test, expect } from '@playwright/test';

// Agent management: tabs, and editing + saving an agent (exercises PUT /api/agents/{id}
// end-to-end — a frontend save that also proves the backend persists).
test.describe('Agent detail', () => {
  test('shows the three management tabs', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Verwalten' }).first().click();
    await expect(page.locator('#f-name')).toHaveValue('HR Urlaubsassistent');

    await page.getByRole('button', { name: 'Berechtigungen' }).click();
    await expect(page.getByText('All_Employees')).toBeVisible();

    await page.getByRole('button', { name: 'Wissensdatenbank' }).click();
    await expect(page.getByText('Betriebsvereinbarung_Urlaub_2024.pdf')).toBeVisible();
  });

  test('rating an agent records feedback', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Verwalten' }).first().click();
    await expect(page.getByText('Bewertung:')).toBeVisible();
    await page.getByTitle('Hilfreich', { exact: true }).click();
    await expect(page.locator('#rate-msg')).toContainText('Danke');
  });

  test('budget tab plans a per-agent budget and mirrors into FinOps', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Verwalten' }).first().click();
    await page.getByRole('button', { name: 'Budget & FinOps' }).click();
    await expect(page.getByText('Budgetplanung')).toBeVisible();
    await expect(page.getByText('Aktuelle Auslastung')).toBeVisible();

    await page.locator('#f-budget').fill('4200');
    await page.getByRole('button', { name: 'Budget speichern' }).click();
    await expect(page.locator('#budget-msg')).toContainText('Gespeichert');

    // Same field shows up in the FinOps table.
    await page.locator('.navbtn[data-view="finops"]').click();
    await expect(page.locator('#view-finops')).toContainText('4.200');
  });

  test('editing the name saves and persists across reload', async ({ page }) => {
    const edited = 'HR Urlaubsassistent (QA)';
    await page.goto('/');
    await page.getByRole('button', { name: 'Verwalten' }).first().click();

    await page.locator('#f-name').fill(edited);
    await page.getByRole('button', { name: 'Speichern', exact: true }).click();
    await expect(page.locator('#save-msg')).toContainText('Gespeichert');

    // Reload → detail again → value came back from the backend.
    await page.reload();
    await page.getByRole('button', { name: 'Verwalten' }).first().click();
    await expect(page.locator('#f-name')).toHaveValue(edited);

    // Restore the original so other specs see the seeded name.
    await page.locator('#f-name').fill('HR Urlaubsassistent');
    await page.getByRole('button', { name: 'Speichern', exact: true }).click();
    await expect(page.locator('#save-msg')).toContainText('Gespeichert');
  });
});
