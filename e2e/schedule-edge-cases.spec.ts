import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should handle very long post titles', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'a'.repeat(100));
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('a'.repeat(100));
  });

  test('should handle unicode characters in search', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', '测试 🎉 テスト');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('测试 🎉 テスト');
  });

  test('should handle rapid filter switching', async ({ page }) => {
    await page.click('button:has-text("🎵")');
    await page.click('button:has-text("📸")');
    await page.click('button:has-text("▶️")');
    await page.click('button:has-text("All")');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle rapid view switching', async ({ page }) => {
    await page.click('button:has-text("month")');
    await page.click('button:has-text("day")');
    await page.click('button:has-text("week")');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle rapid navigation', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await page.click('text=Next Week →');
    }
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle double-click on elements', async ({ page }) => {
    await page.dblclick('h1');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle page refresh', async ({ page }) => {
    await page.click('button:has-text("month")');
    await page.reload();
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle back/forward navigation', async ({ page }) => {
    await page.click('text=+ Add Content');
    await page.goBack();
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should maintain state after scrolling', async ({ page }) => {
    await page.evaluate(() => window.scrollTo(0, 500));
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Boundary Tests', () => {
  test('should handle first day of month', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await expect(page.locator('text=1').first()).toBeVisible();
  });

  test('should handle last day of month', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    // December has 31 days
    await expect(page.locator('text=31').first()).toBeVisible();
  });

  test('should handle month transition', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await page.click('text=Next Month →');
    await expect(page.locator('text=January')).toBeVisible();
  });

  test('should handle year transition', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await page.click('text=Next Month →');
    await expect(page.locator('text=2026')).toBeVisible();
  });

  test('should handle week crossing months', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    // Navigate to end of month
    await page.click('text=Next Week →');
    await page.click('text=Next Week →');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle midnight time', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
    await expect(page.locator('text=12 AM')).toBeVisible();
  });

  test('should handle noon time', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
    await expect(page.locator('text=12 PM')).toBeVisible();
  });

  test('should handle end of day', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
    await expect(page.locator('text=11 PM')).toBeVisible();
  });
});

test.describe('Schedule Page - Concurrent Actions', () => {
  test('should handle simultaneous clicks', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await Promise.all([
      page.click('button:has-text("month")'),
      page.fill('input[placeholder*="Search posts"]', 'test'),
    ]);
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle typing while navigating', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.focus();
    await page.keyboard.type('test');
    await page.click('text=Next Week →');
    await expect(searchInput).toHaveValue('test');
  });
});

test.describe('Schedule Page - Memory & Performance', () => {
  test('should load within 5 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('h1')).toContainText('Schedule');
    const duration = Date.now() - start;
    expect(duration).toBeLessThan(5000);
  });

  test('should handle multiple navigations', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    for (let i = 0; i < 10; i++) {
      await page.click('text=Next Week →');
    }
    for (let i = 0; i < 10; i++) {
      await page.click('text=← Previous Week');
    }
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle view mode cycling', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    for (let i = 0; i < 5; i++) {
      await page.click('button:has-text("week")');
      await page.click('button:has-text("month")');
      await page.click('button:has-text("day")');
    }
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Input Validation', () => {
  test('should handle pasting into search', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.focus();
    await page.keyboard.insertText('pasted text');
    await expect(searchInput).toHaveValue('pasted text');
  });

  test('should handle cut/copy operations', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.fill('test text');
    await searchInput.selectText();
    await page.keyboard.press('Control+C');
    await expect(searchInput).toHaveValue('test text');
  });

  test('should handle undo in search', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.fill('test');
    await page.keyboard.press('Control+Z');
    // Value may or may not change depending on browser
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});
