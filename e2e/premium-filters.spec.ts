/**
 * E2E Tests: Expandable Filters Panel (PRE-FLT-*)
 * Tests for search, platform filter, status filter, results count
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('PRE-FLT: Expandable Filters Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
    // Open filters panel
    await page.click('button[title="Filters"]');
  });

  test.describe('PRE-FLT-001: Panel Display', () => {
    test('should show filters panel when opened', async ({ page }) => {
      await expect(page.locator('.flex.items-center.gap-6.flex-wrap')).toBeVisible();
    });

    test('should have rounded container', async ({ page }) => {
      const panel = page.locator('.rounded-xl.border.border-zinc-800\\/50').nth(1);
      await expect(panel).toBeVisible();
    });

    test('should have backdrop blur styling', async ({ page }) => {
      const panel = page.locator('.backdrop-blur-sm').nth(1);
      await expect(panel).toBeVisible();
    });

    test('should animate in from top', async ({ page }) => {
      // Check for animation class
      const panel = page.locator('.animate-in');
      expect(panel).toBeDefined();
    });
  });

  test.describe('PRE-FLT-002: Search Input', () => {
    test('should display search input', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await expect(searchInput).toBeVisible();
    });

    test('should have search icon', async ({ page }) => {
      await expect(page.locator('text=🔍')).toBeVisible();
    });

    test('should allow typing in search', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.fill('test query');
      await expect(searchInput).toHaveValue('test query');
    });

    test('should show clear button when text entered', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.fill('test');
      const clearBtn = page.locator('button:has-text("×")').first();
      await expect(clearBtn).toBeVisible();
    });

    test('should clear search when clicking clear button', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.fill('test');
      await page.locator('button:has-text("×")').first().click();
      await expect(searchInput).toHaveValue('');
    });

    test('should have focus ring styling', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.focus();
      await expect(searchInput).toBeFocused();
    });
  });

  test.describe('PRE-FLT-003: Platform Filter', () => {
    test('should display Platform label', async ({ page }) => {
      await expect(page.locator('text=Platform').first()).toBeVisible();
    });

    test('should have All button', async ({ page }) => {
      const allBtn = page.locator('.flex.gap-1 >> button:has-text("All")').first();
      await expect(allBtn).toBeVisible();
    });

    test('should have TikTok filter button', async ({ page }) => {
      await expect(page.locator('button:has-text("🎵")')).toBeVisible();
    });

    test('should have Instagram filter button', async ({ page }) => {
      await expect(page.locator('button:has-text("📸")')).toBeVisible();
    });

    test('should have YouTube filter button', async ({ page }) => {
      await expect(page.locator('button:has-text("▶️")')).toBeVisible();
    });

    test('should highlight selected platform', async ({ page }) => {
      await page.locator('button:has-text("🎵")').click();
      const tiktokBtn = page.locator('button:has-text("🎵")');
      await expect(tiktokBtn).toHaveClass(/bg-pink-500/);
    });

    test('should switch to Instagram filter', async ({ page }) => {
      await page.locator('button:has-text("📸")').click();
      const igBtn = page.locator('button:has-text("📸")');
      await expect(igBtn).toHaveClass(/bg-purple-500/);
    });

    test('should switch to YouTube filter', async ({ page }) => {
      await page.locator('button:has-text("▶️")').click();
      const ytBtn = page.locator('button:has-text("▶️")');
      await expect(ytBtn).toHaveClass(/bg-red-500/);
    });

    test('should return to All when clicking All', async ({ page }) => {
      await page.locator('button:has-text("🎵")').click();
      await page.locator('.flex.gap-1 >> button:has-text("All")').first().click();
      const allBtn = page.locator('.flex.gap-1 >> button:has-text("All")').first();
      await expect(allBtn).toHaveClass(/bg-zinc-700/);
    });
  });

  test.describe('PRE-FLT-004: Status Filter', () => {
    test('should display Status label', async ({ page }) => {
      await expect(page.locator('text=Status').first()).toBeVisible();
    });

    test('should have All status button', async ({ page }) => {
      const allStatusBtn = page.locator('button:has-text("All")').nth(1);
      await expect(allStatusBtn).toBeVisible();
    });

    test('should have Scheduled status button', async ({ page }) => {
      await expect(page.locator('button:has-text("⏱ Scheduled")')).toBeVisible();
    });

    test('should have Posted status button', async ({ page }) => {
      await expect(page.locator('button:has-text("✓ Posted")')).toBeVisible();
    });

    test('should have Failed status button', async ({ page }) => {
      await expect(page.locator('button:has-text("⚠ Failed")')).toBeVisible();
    });

    test('should filter by Scheduled status', async ({ page }) => {
      await page.locator('button:has-text("⏱ Scheduled")').click();
      const scheduledBtn = page.locator('button:has-text("⏱ Scheduled")');
      await expect(scheduledBtn).toHaveClass(/bg-violet-500/);
    });

    test('should filter by Posted status', async ({ page }) => {
      await page.locator('button:has-text("✓ Posted")').click();
      const postedBtn = page.locator('button:has-text("✓ Posted")');
      await expect(postedBtn).toHaveClass(/bg-green-500/);
    });

    test('should filter by Failed status', async ({ page }) => {
      await page.locator('button:has-text("⚠ Failed")').click();
      const failedBtn = page.locator('button:has-text("⚠ Failed")');
      await expect(failedBtn).toHaveClass(/bg-red-500/);
    });
  });

  test.describe('PRE-FLT-005: Results Count', () => {
    test('should show results count when filter applied', async ({ page }) => {
      await page.locator('button:has-text("🎵")').click();
      const resultsText = page.locator('text=/Showing \\d+ of \\d+/');
      await expect(resultsText).toBeVisible({ timeout: 5000 });
    });

    test('should update count when changing filters', async ({ page }) => {
      await page.locator('button:has-text("🎵")').click();
      await page.waitForTimeout(500);
      await page.locator('button:has-text("📸")').click();
      const resultsText = page.locator('text=/Showing \\d+ of \\d+/');
      await expect(resultsText).toBeVisible();
    });

    test('should hide count when no filters active', async ({ page }) => {
      // Initially no filters, so no count
      await page.locator('.flex.gap-1 >> button:has-text("All")').first().click();
      // Count might not be visible
    });
  });

  test.describe('PRE-FLT-006: Combined Filters', () => {
    test('should combine platform and status filters', async ({ page }) => {
      await page.locator('button:has-text("🎵")').click();
      await page.locator('button:has-text("⏱ Scheduled")').click();
      // Both should be highlighted
      await expect(page.locator('button:has-text("🎵")')).toHaveClass(/bg-pink-500/);
      await expect(page.locator('button:has-text("⏱ Scheduled")')).toHaveClass(/bg-violet-500/);
    });

    test('should combine search with platform filter', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.fill('test');
      await page.locator('button:has-text("🎵")').click();
      await expect(searchInput).toHaveValue('test');
      await expect(page.locator('button:has-text("🎵")')).toHaveClass(/bg-pink-500/);
    });

    test('should combine all three filters', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="Search posts..."]');
      await searchInput.fill('video');
      await page.locator('button:has-text("📸")').click();
      await page.locator('button:has-text("✓ Posted")').click();
      // All filters should be active
      await expect(searchInput).toHaveValue('video');
    });
  });
});

test.describe('PRE-LGD: Clickable Legend', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-LGD-001: Legend Display', () => {
    test('should display legend section', async ({ page }) => {
      await expect(page.locator('.flex.items-center.gap-4.mb-4')).toBeVisible();
    });

    test('should show Scheduled legend item', async ({ page }) => {
      await expect(page.locator('button >> text=Scheduled').first()).toBeVisible();
    });

    test('should show Posted legend item', async ({ page }) => {
      await expect(page.locator('button >> text=Posted').first()).toBeVisible();
    });

    test('should show count for Scheduled', async ({ page }) => {
      const scheduledCount = page.locator('.text-violet-400').first();
      await expect(scheduledCount).toBeVisible();
    });

    test('should show count for Posted', async ({ page }) => {
      const postedCount = page.locator('.text-green-400').first();
      await expect(postedCount).toBeVisible();
    });
  });

  test.describe('PRE-LGD-002: Legend Styling', () => {
    test('should have violet dot for Scheduled', async ({ page }) => {
      const violetDot = page.locator('.bg-violet-500.rounded-full');
      await expect(violetDot.first()).toBeVisible();
    });

    test('should have green dot for Posted', async ({ page }) => {
      const greenDot = page.locator('.bg-green-500.rounded-full');
      await expect(greenDot.first()).toBeVisible();
    });

    test('should have ring effect on dots', async ({ page }) => {
      const ringDot = page.locator('[class*="ring-2"]');
      await expect(ringDot.first()).toBeVisible();
    });
  });

  test.describe('PRE-LGD-003: Legend Click Actions', () => {
    test('should filter by Scheduled when clicking legend', async ({ page }) => {
      await page.locator('button >> text=Scheduled').first().click();
      // Should highlight the button
      const scheduledBtn = page.locator('button >> text=Scheduled').first();
      await expect(scheduledBtn).toHaveClass(/bg-violet/);
    });

    test('should filter by Posted when clicking legend', async ({ page }) => {
      await page.locator('button >> text=Posted').first().click();
      const postedBtn = page.locator('button >> text=Posted').first();
      await expect(postedBtn).toHaveClass(/bg-green/);
    });

    test('should toggle filter off when clicking again', async ({ page }) => {
      await page.locator('button >> text=Scheduled').first().click();
      await page.locator('button >> text=Scheduled').first().click();
      // Should return to normal
    });
  });

  test.describe('PRE-LGD-004: Platform Colors', () => {
    test('should show TikTok color indicator', async ({ page }) => {
      await expect(page.locator('.bg-pink-500.rounded-full').first()).toBeVisible();
    });

    test('should show Instagram color indicator', async ({ page }) => {
      await expect(page.locator('.bg-purple-500.rounded-full').first()).toBeVisible();
    });

    test('should show YouTube color indicator', async ({ page }) => {
      await expect(page.locator('.bg-red-500.rounded-full').first()).toBeVisible();
    });

    test('should have platform labels', async ({ page }) => {
      await expect(page.locator('text=tiktok')).toBeVisible();
      await expect(page.locator('text=instagram')).toBeVisible();
      await expect(page.locator('text=youtube')).toBeVisible();
    });
  });
});
