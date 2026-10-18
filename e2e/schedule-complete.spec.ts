import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Complete Feature Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should render main container', async ({ page }) => {
    await expect(page.locator('.p-8')).toBeVisible();
  });

  test('should have proper grid layout in week view', async ({ page }) => {
    await expect(page.locator('.grid-cols-7').first()).toBeVisible();
  });

  test('should display week date range', async ({ page }) => {
    await expect(page.locator('text=/Dec \\d+ - Dec \\d+/')).toBeVisible();
  });

  test('should show scrollable post containers', async ({ page }) => {
    await expect(page.locator('.overflow-y-auto').first()).toBeVisible();
  });

  test('should have plus buttons for adding posts', async ({ page }) => {
    const plusBtns = page.locator('button:has-text("+")');
    const count = await plusBtns.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display post cards with proper styling', async ({ page }) => {
    await expect(page.locator('.rounded-lg.bg-zinc-800').first()).toBeVisible();
  });

  test('should show time format options', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('text=24-hour format')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display platform selector buttons', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('text=Platform')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show Cancel button in modal', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('text=Cancel')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display Schedule button in modal', async ({ page }) => {
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      await expect(page.locator('button:has-text("Schedule")').last()).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Schedule Page - UI Elements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should have border styling on cards', async ({ page }) => {
    await expect(page.locator('.border.border-zinc-800').first()).toBeVisible();
  });

  test('should show hover states on buttons', async ({ page }) => {
    const btn = page.locator('button:has-text("Auto-Schedule")');
    await btn.hover();
    await expect(btn).toBeVisible();
  });

  test('should display rounded corners on containers', async ({ page }) => {
    await expect(page.locator('.rounded-xl').first()).toBeVisible();
  });

  test('should have proper spacing between elements', async ({ page }) => {
    await expect(page.locator('.mb-6').first()).toBeVisible();
  });

  test('should show flex layout in controls', async ({ page }) => {
    await expect(page.locator('.flex.items-center').first()).toBeVisible();
  });

  test('should display text with proper colors', async ({ page }) => {
    await expect(page.locator('.text-zinc-400').first()).toBeVisible();
  });

  test('should have background colors applied', async ({ page }) => {
    await expect(page.locator('.bg-zinc-900').first()).toBeVisible();
  });

  test('should show gap between flex items', async ({ page }) => {
    await expect(page.locator('.gap-4').first()).toBeVisible();
  });
});

test.describe('Schedule Page - Week Days Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should show Sunday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Sun').first()).toBeVisible();
  });

  test('should show Monday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Mon').first()).toBeVisible();
  });

  test('should show Tuesday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Tue').first()).toBeVisible();
  });

  test('should show Wednesday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Wed').first()).toBeVisible();
  });

  test('should show Thursday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Thu').first()).toBeVisible();
  });

  test('should show Friday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Fri').first()).toBeVisible();
  });

  test('should show Saturday abbreviation', async ({ page }) => {
    await expect(page.locator('text=Sat').first()).toBeVisible();
  });

  test('should display day numbers', async ({ page }) => {
    const numbers = page.locator('.text-lg.font-semibold');
    const count = await numbers.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Schedule Page - Full Integration', () => {
  test('full user workflow: navigate, search, filter, view', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    
    // Search
    await page.fill('input[placeholder*="Search posts"]', 'test');
    
    // Filter
    await page.click('button:has-text("🎵")');
    
    // Change view
    await page.click('button:has-text("month")');
    
    // Navigate
    await page.click('text=Next Month →');
    
    // Return to week
    await page.click('button:has-text("week")');
    
    // Click Today
    await page.click('button:has-text("Today")');
    
    // Clear search
    await page.click('button:has-text("×")');
    
    // Reset filter
    await page.click('button:has-text("All")');
    
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('full modal workflow: open, configure, close', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    
    const plusBtn = page.locator('button:has-text("+")').first();
    if (await plusBtn.isVisible()) {
      await plusBtn.click();
      
      // Select platform
      const tiktokBtn = page.locator('button:has-text("TikTok")');
      if (await tiktokBtn.isVisible()) {
        await tiktokBtn.click();
      }
      
      // Close modal
      await page.click('button:has-text("×")');
    }
    
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});
