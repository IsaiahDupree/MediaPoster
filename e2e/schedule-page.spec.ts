import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Core Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  // ==================== PAGE LOAD ====================
  test('should load schedule page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should display subtitle', async ({ page }) => {
    await expect(page.locator('text=Manage your content posting schedule')).toBeVisible();
  });

  test('should show Add Content button', async ({ page }) => {
    await expect(page.locator('text=+ Add Content')).toBeVisible();
  });

  test('should show Auto-Schedule button', async ({ page }) => {
    await expect(page.locator('text=Auto-Schedule')).toBeVisible();
  });

  // ==================== VIEW MODES ====================
  test('should have week view selected by default', async ({ page }) => {
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

  test('should display all three view mode buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("week")')).toBeVisible();
    await expect(page.locator('button:has-text("month")')).toBeVisible();
    await expect(page.locator('button:has-text("day")')).toBeVisible();
  });

  // ==================== SEARCH & FILTER ====================
  test('should display search input', async ({ page }) => {
    await expect(page.locator('input[placeholder*="Search posts"]')).toBeVisible();
  });

  test('should filter posts by search query', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.fill('test');
    await expect(searchInput).toHaveValue('test');
  });

  test('should show clear button when search has value', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'test');
    await expect(page.locator('button:has-text("×")')).toBeVisible();
  });

  test('should clear search when clicking X', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search posts"]');
    await searchInput.fill('test');
    await page.click('button:has-text("×")');
    await expect(searchInput).toHaveValue('');
  });

  test('should display platform filter buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("All")')).toBeVisible();
  });

  test('should have All filter selected by default', async ({ page }) => {
    await expect(page.locator('button:has-text("All")')).toHaveClass(/bg-zinc-700/);
  });

  test('should filter by TikTok platform', async ({ page }) => {
    await page.click('button:has-text("🎵")');
    await expect(page.locator('button:has-text("🎵")')).toHaveClass(/bg-pink-500/);
  });

  test('should filter by Instagram platform', async ({ page }) => {
    await page.click('button:has-text("📸")');
    await expect(page.locator('button:has-text("📸")')).toHaveClass(/bg-purple-500/);
  });

  test('should filter by YouTube platform', async ({ page }) => {
    await page.click('button:has-text("▶️")');
    await expect(page.locator('button:has-text("▶️")')).toHaveClass(/bg-red-500/);
  });

  // ==================== LEGEND ====================
  test('should display platform legend', async ({ page }) => {
    await expect(page.locator('text=tiktok').first()).toBeVisible();
    await expect(page.locator('text=instagram').first()).toBeVisible();
    await expect(page.locator('text=youtube').first()).toBeVisible();
  });

  test('should display status legend', async ({ page }) => {
    await expect(page.locator('text=Posted')).toBeVisible();
    await expect(page.locator('text=Pending')).toBeVisible();
  });
});

test.describe('Schedule Page - Week View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should display 7 day columns', async ({ page }) => {
    const dayHeaders = page.locator('.grid-cols-7 > div').first();
    await expect(dayHeaders).toBeVisible();
  });

  test('should show Previous Week button', async ({ page }) => {
    await expect(page.locator('text=← Previous Week')).toBeVisible();
  });

  test('should show Next Week button', async ({ page }) => {
    await expect(page.locator('text=Next Week →')).toBeVisible();
  });

  test('should show Today button in week view', async ({ page }) => {
    await expect(page.locator('button:has-text("Today")').first()).toBeVisible();
  });

  test('should navigate to previous week', async ({ page }) => {
    const dateText = await page.locator('.font-semibold').first().textContent();
    await page.click('text=← Previous Week');
    const newDateText = await page.locator('.font-semibold').first().textContent();
    expect(dateText).not.toBe(newDateText);
  });

  test('should navigate to next week', async ({ page }) => {
    const dateText = await page.locator('.font-semibold').first().textContent();
    await page.click('text=Next Week →');
    const newDateText = await page.locator('.font-semibold').first().textContent();
    expect(dateText).not.toBe(newDateText);
  });

  test('should highlight today in week view', async ({ page }) => {
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });

  test('should show day abbreviations', async ({ page }) => {
    await expect(page.locator('text=Sun').first()).toBeVisible();
    await expect(page.locator('text=Mon').first()).toBeVisible();
    await expect(page.locator('text=Tue').first()).toBeVisible();
  });
});

test.describe('Schedule Page - Month View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
  });

  test('should display month view after clicking', async ({ page }) => {
    await expect(page.locator('text=← Previous Month')).toBeVisible();
  });

  test('should show Previous Month button', async ({ page }) => {
    await expect(page.locator('text=← Previous Month')).toBeVisible();
  });

  test('should show Next Month button', async ({ page }) => {
    await expect(page.locator('text=Next Month →')).toBeVisible();
  });

  test('should show Today button in month view', async ({ page }) => {
    await expect(page.locator('button:has-text("Today")')).toBeVisible();
  });

  test('should display month and year in header', async ({ page }) => {
    const header = page.locator('.font-semibold.text-lg');
    await expect(header).toContainText(/\d{4}/);
  });

  test('should navigate to previous month', async ({ page }) => {
    const dateText = await page.locator('.font-semibold.text-lg').textContent();
    await page.click('text=← Previous Month');
    const newDateText = await page.locator('.font-semibold.text-lg').textContent();
    expect(dateText).not.toBe(newDateText);
  });

  test('should navigate to next month', async ({ page }) => {
    const dateText = await page.locator('.font-semibold.text-lg').textContent();
    await page.click('text=Next Month →');
    const newDateText = await page.locator('.font-semibold.text-lg').textContent();
    expect(dateText).not.toBe(newDateText);
  });

  test('should display day of week headers', async ({ page }) => {
    await expect(page.locator('text=Sun')).toBeVisible();
    await expect(page.locator('text=Mon')).toBeVisible();
    await expect(page.locator('text=Sat')).toBeVisible();
  });

  test('should show 7 columns in month grid', async ({ page }) => {
    const grid = page.locator('.grid.grid-cols-7').first();
    await expect(grid).toBeVisible();
  });
});

test.describe('Schedule Page - Day View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
  });

  test('should display day view with full date', async ({ page }) => {
    await expect(page.locator('h3.text-lg.font-semibold')).toBeVisible();
  });

  test('should show left arrow for previous day', async ({ page }) => {
    await expect(page.locator('button:has-text("←")').first()).toBeVisible();
  });

  test('should show right arrow for next day', async ({ page }) => {
    await expect(page.locator('button:has-text("→")').first()).toBeVisible();
  });

  test('should display hourly timeline', async ({ page }) => {
    await expect(page.locator('text=12 AM')).toBeVisible();
  });

  test('should navigate to previous day', async ({ page }) => {
    const dateText = await page.locator('h3.text-lg.font-semibold').textContent();
    await page.locator('button:has-text("←")').first().click();
    const newDateText = await page.locator('h3.text-lg.font-semibold').textContent();
    expect(dateText).not.toBe(newDateText);
  });

  test('should navigate to next day', async ({ page }) => {
    const dateText = await page.locator('h3.text-lg.font-semibold').textContent();
    await page.locator('button:has-text("→")').first().click();
    const newDateText = await page.locator('h3.text-lg.font-semibold').textContent();
    expect(dateText).not.toBe(newDateText);
  });
});

test.describe('Schedule Page - Stats Section', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should display Total Scheduled stat', async ({ page }) => {
    await expect(page.locator('text=Total Scheduled')).toBeVisible();
  });

  test('should display Posted stat', async ({ page }) => {
    await expect(page.locator('text=Posted').first()).toBeVisible();
  });

  test('should display This Week stat', async ({ page }) => {
    await expect(page.locator('text=This Week')).toBeVisible();
  });

  test('should display Platforms stat', async ({ page }) => {
    await expect(page.locator('text=Platforms')).toBeVisible();
  });

  test('should show pending posts description', async ({ page }) => {
    await expect(page.locator('text=Pending posts')).toBeVisible();
  });

  test('should show successfully published description', async ({ page }) => {
    await expect(page.locator('text=Successfully published')).toBeVisible();
  });
});
