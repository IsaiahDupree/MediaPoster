/**
 * E2E Tests: Premium Calendar Header (PRE-HDR-*)
 * Tests for navigation, view toggle, density mode, filter button, timezone
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('PRE-HDR: Premium Calendar Header', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-HDR-001: Navigation Controls', () => {
    test('should display navigation button group', async ({ page }) => {
      const navGroup = page.locator('.bg-zinc-800\\/80.rounded-lg.p-1').first();
      await expect(navGroup).toBeVisible();
    });

    test('should have previous button', async ({ page }) => {
      const prevBtn = page.locator('button[title="Previous"]');
      await expect(prevBtn).toBeVisible();
    });

    test('should have next button', async ({ page }) => {
      const nextBtn = page.locator('button[title="Next"]');
      await expect(nextBtn).toBeVisible();
    });

    test('should have Today button', async ({ page }) => {
      const todayBtn = page.locator('button:has-text("Today")').first();
      await expect(todayBtn).toBeVisible();
    });

    test('should navigate backward when clicking previous', async ({ page }) => {
      const monthYear = await page.locator('.text-xl.font-bold').textContent();
      await page.click('button[title="Previous"]');
      const newMonthYear = await page.locator('.text-xl.font-bold').textContent();
      expect(newMonthYear).not.toBe(monthYear);
    });

    test('should navigate forward when clicking next', async ({ page }) => {
      const monthYear = await page.locator('.text-xl.font-bold').textContent();
      await page.click('button[title="Next"]');
      const newMonthYear = await page.locator('.text-xl.font-bold').textContent();
      expect(newMonthYear).not.toBe(monthYear);
    });

    test('should jump to current date when clicking Today', async ({ page }) => {
      await page.click('button[title="Previous"]');
      await page.click('button[title="Previous"]');
      await page.click('button:has-text("Today")');
      const now = new Date();
      const monthYear = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      await expect(page.locator('.text-xl.font-bold')).toContainText(monthYear);
    });

    test('should have violet styling on Today button', async ({ page }) => {
      const todayBtn = page.locator('button:has-text("Today")').first();
      await expect(todayBtn).toHaveClass(/text-violet-400/);
    });
  });

  test.describe('PRE-HDR-002: View Mode Toggle', () => {
    test('should display view toggle group', async ({ page }) => {
      const viewToggle = page.locator('button:has-text("month")').locator('..');
      await expect(viewToggle).toBeVisible();
    });

    test('should have Month button', async ({ page }) => {
      await expect(page.locator('button:has-text("month")')).toBeVisible();
    });

    test('should have Week button', async ({ page }) => {
      await expect(page.locator('button:has-text("week")')).toBeVisible();
    });

    test('should have Day button', async ({ page }) => {
      await expect(page.locator('button:has-text("day")')).toBeVisible();
    });

    test('should highlight active view with violet', async ({ page }) => {
      const weekBtn = page.locator('button:has-text("week")');
      await expect(weekBtn).toHaveClass(/bg-violet-500/);
    });

    test('should switch to month view', async ({ page }) => {
      await page.click('button:has-text("month")');
      await expect(page.locator('button:has-text("month")')).toHaveClass(/bg-violet-500/);
    });

    test('should switch to day view', async ({ page }) => {
      await page.click('button:has-text("day")');
      await expect(page.locator('button:has-text("day")')).toHaveClass(/bg-violet-500/);
    });

    test('should have shadow glow on active button', async ({ page }) => {
      const activeBtn = page.locator('button:has-text("week")');
      await expect(activeBtn).toHaveClass(/shadow-lg|shadow-violet/);
    });
  });

  test.describe('PRE-HDR-003: Density Toggle', () => {
    test('should display density toggle group', async ({ page }) => {
      const densityToggle = page.locator('button[title="Compact view"]').locator('..');
      await expect(densityToggle).toBeVisible();
    });

    test('should have compact view button', async ({ page }) => {
      const compactBtn = page.locator('button[title="Compact view"]');
      await expect(compactBtn).toBeVisible();
    });

    test('should have comfortable view button', async ({ page }) => {
      const comfortableBtn = page.locator('button[title="Comfortable view"]');
      await expect(comfortableBtn).toBeVisible();
    });

    test('should toggle to compact mode', async ({ page }) => {
      await page.click('button[title="Compact view"]');
      const compactBtn = page.locator('button[title="Compact view"]');
      await expect(compactBtn).toHaveClass(/bg-zinc-700/);
    });

    test('should toggle to comfortable mode', async ({ page }) => {
      await page.click('button[title="Comfortable view"]');
      const comfortableBtn = page.locator('button[title="Comfortable view"]');
      await expect(comfortableBtn).toHaveClass(/bg-zinc-700/);
    });

    test('should have SVG icon in compact button', async ({ page }) => {
      const svg = page.locator('button[title="Compact view"] svg');
      await expect(svg).toBeVisible();
    });

    test('should have SVG icon in comfortable button', async ({ page }) => {
      const svg = page.locator('button[title="Comfortable view"] svg');
      await expect(svg).toBeVisible();
    });
  });

  test.describe('PRE-HDR-004: Filter Toggle Button', () => {
    test('should display filter toggle button', async ({ page }) => {
      const filterBtn = page.locator('button[title="Filters"]');
      await expect(filterBtn).toBeVisible();
    });

    test('should have filter icon SVG', async ({ page }) => {
      const svg = page.locator('button[title="Filters"] svg');
      await expect(svg).toBeVisible();
    });

    test('should toggle filters panel when clicked', async ({ page }) => {
      await page.click('button[title="Filters"]');
      await expect(page.locator('text=Platform')).toBeVisible();
    });

    test('should highlight filter button when filters open', async ({ page }) => {
      await page.click('button[title="Filters"]');
      const filterBtn = page.locator('button[title="Filters"]');
      await expect(filterBtn).toHaveClass(/bg-violet-500/);
    });

    test('should close filters when clicked again', async ({ page }) => {
      await page.click('button[title="Filters"]');
      await expect(page.locator('text=Platform')).toBeVisible();
      await page.click('button[title="Filters"]');
      await expect(page.locator('.flex.items-center.gap-6.flex-wrap >> text=Platform')).not.toBeVisible();
    });
  });

  test.describe('PRE-HDR-005: Timezone Selector', () => {
    test('should display timezone button', async ({ page }) => {
      const tzBtn = page.locator('button:has-text("🌍")');
      await expect(tzBtn).toBeVisible();
    });

    test('should show current timezone abbreviation', async ({ page }) => {
      const tzBtn = page.locator('button:has-text("🌍")');
      await expect(tzBtn).toContainText(/ET|CT|MT|PT|GMT|CET|JST|AEST|Eastern|Central|Mountain|Pacific/);
    });

    test('should open timezone dropdown when clicked', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      await expect(page.locator('text=Search timezone')).toBeVisible();
    });

    test('should have search input in dropdown', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      const searchInput = page.locator('input[placeholder="Search timezone..."]');
      await expect(searchInput).toBeVisible();
    });

    test('should list all timezone options', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      await expect(page.locator('text=Eastern (ET)')).toBeVisible();
      await expect(page.locator('text=Pacific (PT)')).toBeVisible();
    });

    test('should select new timezone', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      await page.click('text=Pacific (PT)');
      const tzBtn = page.locator('button:has-text("🌍")');
      await expect(tzBtn).toContainText(/Pacific|PT/);
    });

    test('should close dropdown after selection', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      await page.click('text=Pacific (PT)');
      await expect(page.locator('text=Search timezone')).not.toBeVisible();
    });

    test('should highlight selected timezone', async ({ page }) => {
      await page.click('button:has-text("🌍")');
      const selectedTz = page.locator('.bg-violet-500\\/20.text-violet-400');
      await expect(selectedTz).toBeVisible();
    });
  });

  test.describe('PRE-HDR-006: Month/Year Display', () => {
    test('should display current month and year', async ({ page }) => {
      const now = new Date();
      const monthYear = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      await expect(page.locator('.text-xl.font-bold')).toContainText(monthYear);
    });

    test('should have bold white text', async ({ page }) => {
      const monthYear = page.locator('.text-xl.font-bold.text-white');
      await expect(monthYear).toBeVisible();
    });

    test('should update when navigating', async ({ page }) => {
      const initial = await page.locator('.text-xl.font-bold').textContent();
      await page.click('button[title="Next"]');
      const updated = await page.locator('.text-xl.font-bold').textContent();
      expect(updated).not.toBe(initial);
    });
  });

  test.describe('PRE-HDR-007: Header Container Styling', () => {
    test('should have rounded container', async ({ page }) => {
      const header = page.locator('.rounded-xl.border.border-zinc-800\\/50').first();
      await expect(header).toBeVisible();
    });

    test('should have backdrop blur', async ({ page }) => {
      const header = page.locator('.backdrop-blur-sm').first();
      await expect(header).toBeVisible();
    });

    test('should have proper padding', async ({ page }) => {
      const header = page.locator('.p-4.bg-zinc-900\\/80').first();
      await expect(header).toBeVisible();
    });
  });
});
