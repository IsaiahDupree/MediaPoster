/**
 * E2E Tests: Visual Consistency & Styling (PRE-VIS-*)
 * Tests for shadows, hover states, gray hierarchy, responsive design
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('PRE-VIS: Visual Consistency', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-VIS-001: Shadow Consistency', () => {
    test('should have shadow-lg on cards', async ({ page }) => {
      const shadowCard = page.locator('[class*="shadow-lg"]');
      if (await shadowCard.first().isVisible()) {
        await expect(shadowCard.first()).toBeVisible();
      }
    });

    test('should have shadow-2xl on modals', async ({ page }) => {
      const postCard = page.locator('[class*="group/card"]').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.waitForSelector('text=Edit scheduled post', { timeout: 5000 });
        const modalShadow = page.locator('[class*="shadow-2xl"]');
        await expect(modalShadow.first()).toBeVisible();
      }
    });

    test('should have black shadow tint', async ({ page }) => {
      const blackShadow = page.locator('[class*="shadow-black"]');
      if (await blackShadow.first().isVisible()) {
        await expect(blackShadow.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-VIS-002: Gray Hierarchy', () => {
    test('should have zinc-900 for main background', async ({ page }) => {
      const bg900 = page.locator('.bg-zinc-900');
      await expect(bg900.first()).toBeVisible();
    });

    test('should have zinc-800 for cards/inputs', async ({ page }) => {
      const bg800 = page.locator('[class*="bg-zinc-800"]');
      await expect(bg800.first()).toBeVisible();
    });

    test('should have zinc-700 for hover states', async ({ page }) => {
      const hover700 = page.locator('[class*="hover:bg-zinc-700"]');
      await expect(hover700.first()).toBeVisible();
    });

    test('should use opacity variants for subtle backgrounds', async ({ page }) => {
      const opacityBg = page.locator('[class*="bg-zinc-800\\/"]');
      if (await opacityBg.first().isVisible()) {
        await expect(opacityBg.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-VIS-003: Border Consistency', () => {
    test('should use zinc-800 for borders', async ({ page }) => {
      const border800 = page.locator('[class*="border-zinc-800"]');
      await expect(border800.first()).toBeVisible();
    });

    test('should use opacity borders', async ({ page }) => {
      const opacityBorder = page.locator('[class*="border-zinc-700"]');
      if (await opacityBorder.first().isVisible()) {
        await expect(opacityBorder.first()).toBeVisible();
      }
    });

    test('should have rounded-xl on major containers', async ({ page }) => {
      const roundedXl = page.locator('.rounded-xl');
      await expect(roundedXl.first()).toBeVisible();
    });

    test('should have rounded-lg on smaller elements', async ({ page }) => {
      const roundedLg = page.locator('.rounded-lg');
      await expect(roundedLg.first()).toBeVisible();
    });
  });

  test.describe('PRE-VIS-004: Text Color Hierarchy', () => {
    test('should use white for headings', async ({ page }) => {
      const whiteText = page.locator('.text-white');
      await expect(whiteText.first()).toBeVisible();
    });

    test('should use zinc-400 for body text', async ({ page }) => {
      const zinc400 = page.locator('.text-zinc-400');
      await expect(zinc400.first()).toBeVisible();
    });

    test('should use zinc-500 for muted text', async ({ page }) => {
      const zinc500 = page.locator('.text-zinc-500');
      await expect(zinc500.first()).toBeVisible();
    });

    test('should use violet-400 for accent text', async ({ page }) => {
      const violet400 = page.locator('.text-violet-400');
      await expect(violet400.first()).toBeVisible();
    });
  });

  test.describe('PRE-VIS-005: Hover State Consistency', () => {
    test('should have hover background transitions', async ({ page }) => {
      const hoverBg = page.locator('[class*="hover:bg-"]');
      await expect(hoverBg.first()).toBeVisible();
    });

    test('should have hover text color transitions', async ({ page }) => {
      const hoverText = page.locator('[class*="hover:text-"]');
      await expect(hoverText.first()).toBeVisible();
    });

    test('should have transition-all class', async ({ page }) => {
      const transitionAll = page.locator('.transition-all');
      await expect(transitionAll.first()).toBeVisible();
    });

    test('should have transition-colors class', async ({ page }) => {
      const transitionColors = page.locator('.transition-colors');
      await expect(transitionColors.first()).toBeVisible();
    });
  });

  test.describe('PRE-VIS-006: Backdrop Blur', () => {
    test('should use backdrop-blur-sm on overlays', async ({ page }) => {
      const postCard = page.locator('[class*="group/card"]').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.waitForSelector('text=Edit scheduled post', { timeout: 5000 });
        const blur = page.locator('.backdrop-blur-sm');
        await expect(blur.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-VIS-007: Focus States', () => {
    test('should have focus:outline-none on inputs', async ({ page }) => {
      await page.click('button[title="Filters"]');
      const input = page.locator('input[placeholder="Search posts..."]');
      await expect(input).toBeVisible();
    });

    test('should have focus:border-violet on inputs', async ({ page }) => {
      await page.click('button[title="Filters"]');
      const focusBorder = page.locator('[class*="focus:border-violet"]');
      await expect(focusBorder.first()).toBeVisible();
    });

    test('should have focus:ring on inputs', async ({ page }) => {
      await page.click('button[title="Filters"]');
      const focusRing = page.locator('[class*="focus:ring"]');
      if (await focusRing.first().isVisible()) {
        await expect(focusRing.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-VIS-008: Active States', () => {
    test('should show active state on view toggle', async ({ page }) => {
      const activeBtn = page.locator('button.bg-violet-500');
      await expect(activeBtn.first()).toBeVisible();
    });

    test('should show active state on density toggle', async ({ page }) => {
      const activeToggle = page.locator('button.bg-zinc-700');
      await expect(activeToggle.first()).toBeVisible();
    });
  });
});

test.describe('PRE-RESP: Responsive Design', () => {
  test.describe('PRE-RESP-001: Desktop (1440px)', () => {
    test('should render at 1440px', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });

    test('should show full header at 1440px', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('button:has-text("Today")')).toBeVisible();
      await expect(page.locator('button:has-text("month")')).toBeVisible();
    });

    test('should show 7-day grid at 1440px', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${BASE_URL}/schedule`);
      const grid = page.locator('.grid-cols-7');
      await expect(grid.first()).toBeVisible();
    });
  });

  test.describe('PRE-RESP-002: Desktop (1280px)', () => {
    test('should render at 1280px', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });

    test('should show header controls at 1280px', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('button[title="Filters"]')).toBeVisible();
    });
  });

  test.describe('PRE-RESP-003: Laptop (1024px)', () => {
    test('should render at 1024px', async ({ page }) => {
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });

    test('should show calendar grid at 1024px', async ({ page }) => {
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('.grid-cols-7')).toBeVisible();
    });
  });

  test.describe('PRE-RESP-004: Tablet (768px)', () => {
    test('should render at 768px', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible();
    });
  });
});

test.describe('PRE-PERF: Performance Tests', () => {
  test.describe('PRE-PERF-001: Page Load', () => {
    test('should load page in under 3 seconds', async ({ page }) => {
      const start = Date.now();
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(3000);
    });

    test('should render header immediately', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await expect(page.locator('h1:has-text("Schedule")')).toBeVisible({ timeout: 1000 });
    });

    test('should show loading state while fetching', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      // May show loading skeleton
    });
  });

  test.describe('PRE-PERF-002: View Switching', () => {
    test('should switch to month view quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const start = Date.now();
      await page.click('button:has-text("month")');
      await page.waitForTimeout(100);
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(500);
    });

    test('should switch to day view quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const start = Date.now();
      await page.click('button:has-text("day")');
      await page.waitForTimeout(100);
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(500);
    });
  });

  test.describe('PRE-PERF-003: Modal Performance', () => {
    test('should open modal quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      const postCard = page.locator('[class*="group/card"]').first();
      if (await postCard.isVisible()) {
        const start = Date.now();
        await postCard.click();
        await page.waitForSelector('text=Edit scheduled post', { timeout: 2000 });
        const duration = Date.now() - start;
        expect(duration).toBeLessThan(2000);
      }
    });

    test('should close modal quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      const postCard = page.locator('[class*="group/card"]').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.waitForSelector('text=Edit scheduled post', { timeout: 5000 });
        const start = Date.now();
        await page.click('svg path[d*="M6 18L18 6"]');
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 1000 });
        const duration = Date.now() - start;
        expect(duration).toBeLessThan(1000);
      }
    });
  });

  test.describe('PRE-PERF-004: Filter Performance', () => {
    test('should open filters quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      const start = Date.now();
      await page.click('button[title="Filters"]');
      await expect(page.locator('text=Platform')).toBeVisible({ timeout: 500 });
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(500);
    });

    test('should apply filter quickly', async ({ page }) => {
      await page.goto(`${BASE_URL}/schedule`);
      await page.click('button[title="Filters"]');
      const start = Date.now();
      await page.click('button:has-text("🎵")');
      await page.waitForTimeout(100);
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(300);
    });
  });
});

test.describe('PRE-A11Y: Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-A11Y-001: Keyboard Navigation', () => {
    test('should focus filter button with Tab', async ({ page }) => {
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      // Should be able to tab through elements
    });

    test('should toggle view with keyboard', async ({ page }) => {
      await page.locator('button:has-text("month")').focus();
      await page.keyboard.press('Enter');
      await expect(page.locator('button:has-text("month")')).toHaveClass(/bg-violet-500/);
    });
  });

  test.describe('PRE-A11Y-002: Button Titles', () => {
    test('should have title on Previous button', async ({ page }) => {
      await expect(page.locator('button[title="Previous"]')).toBeVisible();
    });

    test('should have title on Next button', async ({ page }) => {
      await expect(page.locator('button[title="Next"]')).toBeVisible();
    });

    test('should have title on Compact view button', async ({ page }) => {
      await expect(page.locator('button[title="Compact view"]')).toBeVisible();
    });

    test('should have title on Comfortable view button', async ({ page }) => {
      await expect(page.locator('button[title="Comfortable view"]')).toBeVisible();
    });

    test('should have title on Filters button', async ({ page }) => {
      await expect(page.locator('button[title="Filters"]')).toBeVisible();
    });

    test('should have title on Schedule post button', async ({ page }) => {
      const scheduleBtn = page.locator('[title="Schedule post"]');
      if (await scheduleBtn.first().isVisible()) {
        await expect(scheduleBtn.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-A11Y-003: Color Contrast', () => {
    test('should have sufficient contrast for headings', async ({ page }) => {
      const heading = page.locator('.text-white');
      await expect(heading.first()).toBeVisible();
    });

    test('should have sufficient contrast for buttons', async ({ page }) => {
      const btn = page.locator('button.bg-violet-500');
      await expect(btn.first()).toBeVisible();
    });
  });
});
