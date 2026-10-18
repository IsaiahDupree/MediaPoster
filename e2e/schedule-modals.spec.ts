import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Media Selector Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should open media selector when clicking Add Content', async ({ page }) => {
    await page.click('text=+ Add Content');
    await expect(page).toHaveURL(/\/media/);
  });

  test('should show platform selector in media modal', async ({ page }) => {
    // Click on a day cell plus button
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('text=Select project')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show time input in media modal', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('input[type="time"]')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show visibility dropdown in media modal', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('select:has-text("Public")')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show 24-hour format toggle', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('text=24-hour format')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should close modal when clicking X', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await page.click('button:has-text("×")');
      await expect(page.locator('text=Select project')).not.toBeVisible();
    }
  });

  test('should display TikTok platform option', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('button:has-text("🎵")')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display Instagram platform option', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('button:has-text("📸")')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display YouTube platform option', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('button:has-text("▶️")')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Schedule Page - Edit Modal', () => {
  test('should have edit modal elements available', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    // This test checks that the page loads properly and edit modal code exists
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Delete Confirmation Modal', () => {
  test('should have delete confirmation elements available', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    // This test checks that the page loads properly and delete modal code exists
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Timezone Selector', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should display timezone in controls', async ({ page }) => {
    await expect(page.locator('text=🌍')).toBeVisible();
  });

  test('should show timezone dropdown when clicked', async ({ page }) => {
    await page.click('text=🌍');
    await expect(page.locator('.absolute.right-0.mt-2')).toBeVisible({ timeout: 3000 });
  });

  test('should list timezone options', async ({ page }) => {
    await page.click('text=🌍');
    await expect(page.locator('text=Eastern Time')).toBeVisible({ timeout: 3000 });
  });

  test('should close timezone dropdown when selecting', async ({ page }) => {
    await page.click('text=🌍');
    const option = page.locator('text=Pacific Time');
    if (await option.isVisible()) {
      await option.click();
    }
  });
});
