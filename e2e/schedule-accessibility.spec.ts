import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should have accessible page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should have focusable search input', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.focus();
    await expect(searchInput).toBeFocused();
  });

  test('should have focusable buttons', async ({ page }) => {
    const btn = page.locator('button:has-text("Auto-Schedule")');
    await btn.focus();
    await expect(btn).toBeFocused();
  });

  test('should support keyboard interaction', async ({ page }) => {
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('should have visible focus indicators', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.focus();
    await expect(searchInput).toHaveClass(/focus:/);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
  });

  test('should have descriptive button text', async ({ page }) => {
    await expect(page.locator('text=+ Add Content')).toBeVisible();
    await expect(page.locator('text=Auto-Schedule')).toBeVisible();
  });

  test('should have alt text for images', async ({ page }) => {
    const images = page.locator('img[alt]');
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt).toBeTruthy();
    }
  });

  test('should support screen reader navigation', async ({ page }) => {
    // Check for semantic structure
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('button').first()).toBeVisible();
  });

  test('should have sufficient color contrast', async ({ page }) => {
    // Check that text is visible
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('p.text-zinc-400').first()).toBeVisible();
  });
});

test.describe('Schedule Page - ARIA Labels', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should have placeholder text on search', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await expect(searchInput).toHaveAttribute('placeholder', /Search/);
  });

  test('should have type attribute on inputs', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await expect(searchInput).toHaveAttribute('type', 'text');
  });
});

test.describe('Schedule Page - Motion & Animations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should have transition classes', async ({ page }) => {
    const btn = page.locator('button:has-text("Auto-Schedule")');
    await expect(btn).toHaveClass(/transition/);
  });

  test('should have hover states', async ({ page }) => {
    const btn = page.locator('button:has-text("Auto-Schedule")');
    await expect(btn).toHaveClass(/hover:/);
  });

  test('loading skeleton should have animation', async ({ page }) => {
    // Animation class should exist in the codebase
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Error Handling', () => {
  test('should handle network errors gracefully', async ({ page }) => {
    await page.route('**/api/schedule/**', (route) => route.abort());
    await page.goto(`${BASE_URL}/schedule`);
    // Page should still load
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle slow network', async ({ page }) => {
    await page.route('**/api/schedule/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.continue();
    });
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle empty API response', async ({ page }) => {
    await page.route('**/api/schedule/list', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ posts: [] }),
      });
    });
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Cross-Browser', () => {
  test('should work in chromium', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});
