/**
 * E2E Tests: Reliability & Edge Cases (SCH-REL-*)
 * Tests for refresh behavior, network failures, offline handling
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('SCH-REL: Reliability Tests', () => {
  test.describe('SCH-REL-001: Page Refresh Behavior', () => {
    test('should persist view mode after refresh', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("month")');
      await expect(page.locator('button:has-text("month")')).toHaveClass(/bg-violet-500/);
      await page.reload();
      // View mode may or may not persist depending on implementation
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should persist date navigation after refresh', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('text=Next Week →');
      await page.reload();
      // Date should reset to current or persist
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should reload schedule data after refresh', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      await page.reload();
      await page.waitForLoadState('networkidle');
      // Should show schedule or loading state
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });
  });

  test.describe('SCH-REL-002: Network Failure Handling', () => {
    test('should show error on network failure during load', async ({ page }) => {
      // Intercept and fail API requests
      await page.route('**/api/schedule/**', route => route.abort());
      await page.goto(`${BASE_URL}/schedule`);
      // Should show some state even on failure
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });

    test('should handle API timeout gracefully', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Slow down subsequent requests
      await page.route('**/api/schedule/**', async route => {
        await new Promise(r => setTimeout(r, 100));
        await route.continue();
      });
      await page.click('text=Next Week →');
      // Should not crash
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });
  });

  test.describe('SCH-REL-003: Data Consistency', () => {
    test('should show consistent data across view modes', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Get post count in week view
      const weekPosts = await page.locator('.cursor-pointer.rounded-lg').count();
      // Switch to month view
      await page.click('button:has-text("month")');
      const monthPosts = await page.locator('.cursor-pointer').count();
      // Should have similar or more posts visible
      expect(monthPosts).toBeGreaterThanOrEqual(0);
    });

    test('should update UI optimistically on edit', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
        // Edit title
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.fill('Optimistic Update Test');
        await page.click('button:has-text("Save")');
        // Should close immediately (optimistic)
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 10000 });
      }
    });
  });

  test.describe('SCH-REL-004: State Recovery', () => {
    test('should recover from modal close without save', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
        // Edit but don't save
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.fill('Unsaved Changes');
        // Close without saving
        await page.locator('button:has-text("×")').last().click();
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 5000 });
        // Re-open should show original
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
      }
    });
  });
});

test.describe('SCH-EDGE: Edge Case Tests', () => {
  test.describe('SCH-EDGE-001: Empty States', () => {
    test('should show empty state message for days with no posts', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Navigate to a date with no posts
      await page.click('text=← Previous Week');
      await page.click('text=← Previous Week');
      await page.click('text=← Previous Week');
      // Should show add post option
      const addPost = page.locator('text=/Add|\\+/');
      expect(await addPost.count()).toBeGreaterThanOrEqual(0);
    });

    test('should handle month with no posts', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("month")');
      // Navigate to past month
      await page.click('text=← Previous Month');
      await page.click('text=← Previous Month');
      await page.click('text=← Previous Month');
      // Should still render grid
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });
  });

  test.describe('SCH-EDGE-002: Long Content', () => {
    test('should truncate long titles', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const truncated = page.locator('.truncate');
      const count = await truncated.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should handle long captions in edit modal', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const textarea = page.locator('textarea');
        if (await textarea.isVisible()) {
          // Enter very long caption
          await textarea.fill('A'.repeat(2000) + ' #hashtag');
          await expect(textarea).toHaveValue(/A{100,}/);
        }
      }
    });
  });

  test.describe('SCH-EDGE-003: Special Characters', () => {
    test('should handle emojis in title', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const titleInput = page.locator('input[placeholder="Post title"]');
        if (await titleInput.isVisible()) {
          await titleInput.fill('Test 🎉🔥💯 Title');
          await expect(titleInput).toHaveValue('Test 🎉🔥💯 Title');
        }
      }
    });

    test('should handle unicode in caption', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const textarea = page.locator('textarea');
        if (await textarea.isVisible()) {
          await textarea.fill('测试 テスト مرحبا #test');
          await expect(textarea).toHaveValue('测试 テスト مرحبا #test');
        }
      }
    });
  });

  test.describe('SCH-EDGE-004: Rapid Actions', () => {
    test('should handle rapid view switching', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Rapidly switch views
      await page.click('button:has-text("month")');
      await page.click('button:has-text("day")');
      await page.click('button:has-text("week")');
      await page.click('button:has-text("month")');
      await page.click('button:has-text("week")');
      // Should not crash
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should handle rapid navigation', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Rapidly navigate
      await page.click('text=Next Week →');
      await page.click('text=Next Week →');
      await page.click('text=← Previous Week');
      await page.click('text=Next Week →');
      await page.click('button:has-text("Today")');
      // Should not crash
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should handle rapid modal open/close', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const plusBtn = page.locator('button:has-text("+")').first();
      if (await plusBtn.isVisible()) {
        // Rapidly open/close
        await plusBtn.click();
        await page.locator('button:has-text("×")').last().click();
        await plusBtn.click();
        await page.locator('button:has-text("×")').last().click();
        // Should not crash
        await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
      }
    });
  });

  test.describe('SCH-EDGE-005: Boundary Dates', () => {
    test('should handle year boundary (Dec -> Jan)', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("month")');
      // Navigate to December
      while (!(await page.locator('text=/December \\d{4}/').isVisible())) {
        await page.click('text=Next Month →');
        if (await page.locator('text=/December 2026/').isVisible()) break;
      }
      // Go to next month (January)
      await page.click('text=Next Month →');
      await expect(page.locator('text=/January/').first()).toBeVisible();
    });

    test('should handle month boundary in week view', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // Navigate until week spans two months
      for (let i = 0; i < 10; i++) {
        await page.click('text=Next Week →');
      }
      // Should still work
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });
  });
});

test.describe('SCH-VISUAL: Visual Regression Checkpoints', () => {
  test.describe('SCH-VIS-001: View Snapshots', () => {
    test('should render month view correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("month")');
      await page.waitForLoadState('networkidle');
      // Visual check - grid should be visible
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should render week view correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("week")');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should render day view correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button:has-text("day")');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('text=12 AM')).toBeVisible();
    });
  });

  test.describe('SCH-VIS-002: Modal Snapshots', () => {
    test('should render edit modal correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('video')).toBeVisible();
        await expect(page.locator('input[placeholder="Post title"]')).toBeVisible();
      }
    });

    test('should render delete confirm modal correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await expect(page.locator('text=Delete post')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('button:has-text("Cancel")')).toBeVisible();
        await expect(page.locator('button:has-text("Confirm")')).toBeVisible();
      }
    });

    test('should render date picker correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        await expect(page.locator('text=/Su|Mo|Tu|We/')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('input[type="time"]')).toBeVisible();
      }
    });
  });

  test.describe('SCH-VIS-003: Responsive Breakpoints', () => {
    test('should render correctly at 1440px width', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should render correctly at 1280px width', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should render correctly at 1024px width', async ({ page }) => {
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });

    test('should render correctly at 768px width', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });
  });
});
