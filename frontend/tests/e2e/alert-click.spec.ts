import { test, expect } from "@playwright/test";

test("alert click", async ({ page }) => {
  await page.goto("/");
  // wait for alerts table to load (mock data fallback)
  const firstRow = page.getByTestId(/^alert-row-/).first();
  await expect(firstRow).toBeVisible({ timeout: 5000 });
  const count = await page.getByTestId(/^alert-row-/).count();
  expect(count).toBeGreaterThan(0);
  await firstRow.click();
  // evidence panel should become visible within 500ms after click
  await expect(page.getByTestId("evidence-panel")).toBeVisible({ timeout: 500 });
  // check SHAP bars visible or nl text — panel contains flagged/Evidence/Select
  await expect(page.getByTestId("evidence-panel")).toContainText(/flagged|Evidence|Select/i, { timeout: 500 });
});
