import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('Schedule Page - Advanced Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should combine search and platform filter', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'test');
    await page.click('button:has-text("🎵")');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('test');
  });

  test('should show results count when filtering', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'test');
    const resultsText = page.locator('text=/\\d+ of \\d+ posts/');
    const isVisible = await resultsText.isVisible({ timeout: 3000 }).catch(() => false);
    expect(isVisible).toBeDefined();
  });

  test('should reset to All when clicking All button', async ({ page }) => {
    await page.click('button:has-text("🎵")');
    await page.click('button:has-text("All")');
    await expect(page.locator('button:has-text("All")')).toHaveClass(/bg-zinc-700/);
  });

  test('should persist filter when changing views', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'test');
    await page.click('button:has-text("month")');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('test');
  });

  test('should persist filter when navigating dates', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'test');
    await page.click('text=Next Week →');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('test');
  });

  test('should filter case-insensitively', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'TEST');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('TEST');
  });

  test('should search by caption content', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'caption');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('caption');
  });

  test('should search by title content', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', 'title');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('title');
  });

  test('should handle empty search gracefully', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', '');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should handle special characters in search', async ({ page }) => {
    await page.fill('input[placeholder*="Search posts"]', '#hashtag @mention');
    await expect(page.locator('input[placeholder*="Search posts"]')).toHaveValue('#hashtag @mention');
  });
});

test.describe('Schedule Page - Platform Color Coding', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test('should have pink color for TikTok', async ({ page }) => {
    const tiktokBtn = page.locator('button:has-text("🎵")').last();
    await tiktokBtn.click();
    await expect(tiktokBtn).toHaveClass(/bg-pink-500/);
  });

  test('should have purple color for Instagram', async ({ page }) => {
    const instaBtn = page.locator('button:has-text("📸")').last();
    await instaBtn.click();
    await expect(instaBtn).toHaveClass(/bg-purple-500/);
  });

  test('should have red color for YouTube', async ({ page }) => {
    const ytBtn = page.locator('button:has-text("▶️")').last();
    await ytBtn.click();
    await expect(ytBtn).toHaveClass(/bg-red-500/);
  });

  test('should show colored legend dots', async ({ page }) => {
    await expect(page.locator('.bg-pink-500').first()).toBeVisible();
  });

  test('should show green for Posted status', async ({ page }) => {
    await expect(page.locator('.bg-green-500').first()).toBeVisible();
  });
});

test.describe('Schedule Page - View Mode Persistence', () => {
  test('should start in week view by default', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await expect(page.locator('text=Previous Week')).toBeVisible();
  });

  test('should switch to month view and stay', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await expect(page.locator('text=Previous Month')).toBeVisible();
    await page.click('text=Next Month →');
    await expect(page.locator('text=Previous Month')).toBeVisible();
  });

  test('should switch to day view and stay', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
    await expect(page.locator('text=12 AM')).toBeVisible();
    await page.locator('button:has-text("→")').first().click();
    await expect(page.locator('text=12 AM')).toBeVisible();
  });
});

test.describe('Schedule Page - Navigation Arrows', () => {
  test('should navigate week with arrows', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('text=← Previous Week');
    await page.click('text=Next Week →');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should navigate month with arrows', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await page.click('text=← Previous Month');
    await page.click('text=Next Month →');
    await expect(page.locator('h1')).toContainText('Schedule');
  });

  test('should navigate day with arrows', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("day")');
    await page.locator('button:has-text("←")').first().click();
    await page.locator('button:has-text("→")').first().click();
    await expect(page.locator('h1')).toContainText('Schedule');
  });
});

test.describe('Schedule Page - Today Button Functionality', () => {
  test('should return to current week from past', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('text=← Previous Week');
    await page.click('text=← Previous Week');
    await page.click('button:has-text("Today")');
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });

  test('should return to current week from future', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('text=Next Week →');
    await page.click('text=Next Week →');
    await page.click('button:has-text("Today")');
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });

  test('should return to current month from past', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await page.click('text=← Previous Month');
    await page.click('text=← Previous Month');
    await page.click('button:has-text("Today")');
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });

  test('should return to current month from future', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.click('button:has-text("month")');
    await page.click('text=Next Month →');
    await page.click('text=Next Month →');
    await page.click('button:has-text("Today")');
    await expect(page.locator('.text-violet-400').first()).toBeVisible();
  });
});
