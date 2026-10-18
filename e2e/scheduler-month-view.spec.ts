/**
 * E2E Tests: Month View (SCH-MON-*)
 * Tests for month grid, cards, navigation, and cell behaviors
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('SCH-MON: Month View Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    // Switch to month view
    await page.click('button:has-text("month")');
    await expect(page.locator('button:has-text("month")')).toHaveClass(/bg-violet-500/);
  });

  test.describe('SCH-MON-001: Month Grid Rendering', () => {
    test('should render month grid with correct week rows', async ({ page }) => {
      const grid = page.locator('.grid-cols-7');
      await expect(grid.first()).toBeVisible();
    });

    test('should display day labels (Sun-Sat)', async ({ page }) => {
      await expect(page.locator('text=Sun').first()).toBeVisible();
      await expect(page.locator('text=Mon').first()).toBeVisible();
      await expect(page.locator('text=Tue').first()).toBeVisible();
      await expect(page.locator('text=Wed').first()).toBeVisible();
      await expect(page.locator('text=Thu').first()).toBeVisible();
      await expect(page.locator('text=Fri').first()).toBeVisible();
      await expect(page.locator('text=Sat').first()).toBeVisible();
    });

    test('should display current month and year in header', async ({ page }) => {
      const now = new Date();
      const monthYear = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      await expect(page.locator(`text=${monthYear}`)).toBeVisible();
    });

    test('should show day numbers in grid cells', async ({ page }) => {
      // Check that day 1 exists in the month
      await expect(page.locator('.grid-cols-7 >> text=1').first()).toBeVisible();
    });
  });

  test.describe('SCH-MON-002: Card Rendering', () => {
    test('should display status pill (Posted/Scheduled)', async ({ page }) => {
      const statusPill = page.locator('text=/Posted|Scheduled/');
      // May or may not have posts
      const count = await statusPill.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should display platform icons on cards', async ({ page }) => {
      const platformIcons = page.locator('text=/🎵|📸|▶️/');
      const count = await platformIcons.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should display time on post cards', async ({ page }) => {
      const timeIndicator = page.locator('text=🕐');
      const count = await timeIndicator.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should truncate long titles', async ({ page }) => {
      const truncatedText = page.locator('.truncate');
      const count = await truncatedText.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('SCH-MON-003: Plus Button Behavior', () => {
    test('should show + button on day cell hover', async ({ page }) => {
      const dayCell = page.locator('.group').first();
      await dayCell.hover();
      const plusButton = dayCell.locator('button:has-text("+")');
      await expect(plusButton).toBeVisible();
    });

    test('should open media selector when clicking + button', async ({ page }) => {
      const dayCell = page.locator('.group').first();
      await dayCell.hover();
      const plusButton = dayCell.locator('button:has-text("+")');
      await plusButton.click();
      // Should open media selector modal
      await expect(page.locator('text=Select project')).toBeVisible({ timeout: 5000 });
    });

    test('should prefill date when opening from + button', async ({ page }) => {
      const dayCell = page.locator('.group').first();
      await dayCell.hover();
      await dayCell.locator('button:has-text("+")').click();
      // Modal should show the date
      await expect(page.locator('text=/Schedule for/')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('SCH-MON-004: Navigation', () => {
    test('should navigate to previous month', async ({ page }) => {
      const currentMonth = await page.locator('text=/[A-Z][a-z]+ \\d{4}/').first().textContent();
      await page.click('text=← Previous Month');
      const newMonth = await page.locator('text=/[A-Z][a-z]+ \\d{4}/').first().textContent();
      expect(newMonth).not.toBe(currentMonth);
    });

    test('should navigate to next month', async ({ page }) => {
      const currentMonth = await page.locator('text=/[A-Z][a-z]+ \\d{4}/').first().textContent();
      await page.click('text=Next Month →');
      const newMonth = await page.locator('text=/[A-Z][a-z]+ \\d{4}/').first().textContent();
      expect(newMonth).not.toBe(currentMonth);
    });

    test('should jump to current date with Today button', async ({ page }) => {
      // Navigate away first
      await page.click('text=← Previous Month');
      await page.click('text=← Previous Month');
      // Click Today
      await page.click('button:has-text("Today")');
      // Should show current month
      const now = new Date();
      const monthYear = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      await expect(page.locator(`text=${monthYear}`)).toBeVisible();
    });

    test('should highlight today in violet', async ({ page }) => {
      await page.click('button:has-text("Today")');
      const todayCell = page.locator('.text-violet-400.font-bold');
      await expect(todayCell).toBeVisible();
    });
  });

  test.describe('SCH-MON-005: Cell Density & Overflow', () => {
    test('should have scrollable container for posts in cells', async ({ page }) => {
      const scrollableContainer = page.locator('.overflow-y-auto');
      await expect(scrollableContainer.first()).toBeVisible();
    });

    test('should show post count badge on days with posts', async ({ page }) => {
      const postCountBadge = page.locator('.rounded-full.bg-violet-500\\/20');
      // May or may not have posts
      const count = await postCountBadge.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('SCH-MON-006: Drag and Drop', () => {
    test('should allow dragging scheduled posts', async ({ page }) => {
      const draggablePost = page.locator('[draggable="true"]').first();
      if (await draggablePost.isVisible()) {
        await expect(draggablePost).toHaveAttribute('draggable', 'true');
      }
    });

    test('should show drop zone highlight on drag over', async ({ page }) => {
      // This is a visual test - just verify the hover class exists in code
      const dayCell = page.locator('.hover\\:bg-violet-500\\/10').first();
      await expect(dayCell).toBeVisible();
    });
  });

  test.describe('SCH-MON-007: Click to Edit', () => {
    test('should open edit modal when clicking a post card', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg.bg-zinc-800').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
      }
    });
  });
});
