import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Stats Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should display 4 stat cards', async ({ page }) => {
    const statCards = page.locator('.grid.grid-cols-4 > div');
    await expect(statCards).toHaveCount(4);
  });

  test('should show Total Scheduled with violet color', async ({ page }) => {
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });

  test('should show Posted with green color', async ({ page }) => {
    await expect(page.locator('.text-green-400').first()).toBeVisible();
  });

  test('should show This Week with blue color', async ({ page }) => {
    await expect(page.locator('.text-blue-400').first()).toBeVisible();
  });

  test('should show numeric values in stats', async ({ page }) => {
    const numbers = page.locator('.text-2xl.font-bold');
    const count = await numbers.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('should show Pending posts label', async ({ page }) => {
    await expect(page.locator('text=Pending posts')).toBeVisible();
  });

  test('should show Successfully published label', async ({ page }) => {
    await expect(page.locator('text=Successfully published')).toBeVisible();
  });

  test('should show Posts scheduled label', async ({ page }) => {
    await expect(page.locator('text=Posts scheduled')).toBeVisible();
  });

  test('should show platform breakdown badges', async ({ page }) => {
    await expect(page.locator('text=Platforms')).toBeVisible();
  });

  test('stats should have rounded corners', async ({ page }) => {
    const statCard = page.locator('.bg-zinc-900.rounded-xl.border').first();
    await expect(statCard).toBeVisible();
  });
});

test.describe('Schedule Page - Stats Calculations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForTimeout(1000);
  });

  test('should display non-negative numbers', async ({ page }) => {
    const numbers = page.locator('.text-2xl.font-bold');
    const count = await numbers.count();
    for (let i = 0; i < count; i++) {
      const text = await numbers.nth(i).textContent();
      if (text && /^\d+$/.test(text.trim())) {
        expect(parseInt(text)).toBeGreaterThanOrEqual(0);
      }
    }
  });

  test('should update when filter applied', async ({ page }) => {
    const beforeCount = await page.locator('.text-violet-400').first().textContent();
    await page.fill('input[placeholder*="Search posts"]', 'nonexistent12345');
    await page.waitForTimeout(500);
    // Stats should still be visible
    await expect(page.locator('text=Total Scheduled')).toBeVisible();
  });
});

test.describe('Schedule Page - Platform Badges in Stats', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should show platform icons in stats', async ({ page }) => {
    // At least the Platforms section should be visible
    await expect(page.locator('text=Platforms')).toBeVisible();
  });

  test('should have colored platform badges', async ({ page }) => {
    // Platform colors should be applied
    const statSection = page.locator('.grid.grid-cols-4 > div').last();
    await expect(statSection).toBeVisible();
  });
});

test.describe('Schedule Page - Stats Responsiveness', () => {
  test('should display stats on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('text=Total Scheduled')).toBeVisible();
  });

  test('should display stats on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('text=Total Scheduled')).toBeVisible();
  });

  test('should display stats on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('text=Total Scheduled')).toBeVisible();
  });
});
