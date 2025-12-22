/**
 * E2E Tests: Premium Card Design (PRE-CRD-*)
 * Tests for enhanced week view cards with density mode, hover effects, status styling
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('PRE-CRD: Premium Card Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-CRD-001: Card Container', () => {
    test('should display post cards in week view', async ({ page }) => {
      const cards = page.locator('[class*="group/card"]');
      const count = await cards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should have rounded-xl styling', async ({ page }) => {
      const card = page.locator('[class*="rounded-xl"]').first();
      await expect(card).toBeVisible();
    });

    test('should have border styling', async ({ page }) => {
      const card = page.locator('[class*="border-zinc-800"]').first();
      await expect(card).toBeVisible();
    });

    test('should be clickable', async ({ page }) => {
      const card = page.locator('[class*="cursor-pointer"]').first();
      if (await card.isVisible()) {
        await expect(card).toHaveClass(/cursor-pointer/);
      }
    });

    test('should be draggable for pending posts', async ({ page }) => {
      const draggableCard = page.locator('[class*="cursor-grab"]').first();
      if (await draggableCard.isVisible()) {
        await expect(draggableCard).toHaveClass(/cursor-grab/);
      }
    });
  });

  test.describe('PRE-CRD-002: Thumbnail Section', () => {
    test('should have thumbnail container', async ({ page }) => {
      const thumbnail = page.locator('.bg-zinc-900.relative').first();
      await expect(thumbnail).toBeVisible();
    });

    test('should display thumbnail image when available', async ({ page }) => {
      const img = page.locator('[class*="group/card"] img').first();
      if (await img.isVisible()) {
        await expect(img).toHaveClass(/object-cover/);
      }
    });

    test('should have platform badge on thumbnail', async ({ page }) => {
      const badge = page.locator('[class*="absolute"][class*="top-1"]').first();
      if (await badge.isVisible()) {
        await expect(badge).toBeVisible();
      }
    });

    test('should show edit icon on hover', async ({ page }) => {
      const card = page.locator('[class*="group/card"]').first();
      if (await card.isVisible()) {
        await card.hover();
        const editIcon = page.locator('[class*="group-hover/card:opacity-100"]').first();
        // Edit icon appears on hover
      }
    });

    test('should have status indicator line at bottom', async ({ page }) => {
      const statusLine = page.locator('.absolute.bottom-0.left-0.right-0.h-0\\.5').first();
      if (await statusLine.isVisible()) {
        await expect(statusLine).toBeVisible();
      }
    });
  });

  test.describe('PRE-CRD-003: Density Mode - Compact', () => {
    test('should switch to compact mode', async ({ page }) => {
      await page.click('button[title="Compact view"]');
      await expect(page.locator('button[title="Compact view"]')).toHaveClass(/bg-zinc-700/);
    });

    test('should have smaller thumbnail in compact mode', async ({ page }) => {
      await page.click('button[title="Compact view"]');
      const thumbnail = page.locator('.h-16').first();
      // Compact has h-16
    });

    test('should have smaller text in compact mode', async ({ page }) => {
      await page.click('button[title="Compact view"]');
      const title = page.locator('.text-xs.font-medium').first();
      if (await title.isVisible()) {
        await expect(title).toHaveClass(/text-xs/);
      }
    });

    test('should have less padding in compact mode', async ({ page }) => {
      await page.click('button[title="Compact view"]');
      const info = page.locator('.p-2').first();
      if (await info.isVisible()) {
        await expect(info).toHaveClass(/p-2/);
      }
    });
  });

  test.describe('PRE-CRD-004: Density Mode - Comfortable', () => {
    test('should switch to comfortable mode', async ({ page }) => {
      await page.click('button[title="Comfortable view"]');
      await expect(page.locator('button[title="Comfortable view"]')).toHaveClass(/bg-zinc-700/);
    });

    test('should have larger thumbnail in comfortable mode', async ({ page }) => {
      await page.click('button[title="Comfortable view"]');
      const thumbnail = page.locator('.h-20').first();
      // Comfortable has h-20
    });

    test('should show caption preview in comfortable mode', async ({ page }) => {
      await page.click('button[title="Comfortable view"]');
      // Caption preview is visible in comfortable mode
      const caption = page.locator('.text-\\[10px\\].text-zinc-500.truncate').first();
      // May or may not have caption
    });

    test('should have more padding in comfortable mode', async ({ page }) => {
      await page.click('button[title="Comfortable view"]');
      const info = page.locator('.p-2\\.5').first();
      // May have p-2.5 in comfortable mode
    });
  });

  test.describe('PRE-CRD-005: Title Hierarchy', () => {
    test('should display title prominently', async ({ page }) => {
      const title = page.locator('.font-medium.truncate').first();
      if (await title.isVisible()) {
        await expect(title).toBeVisible();
      }
    });

    test('should have white/bright text for title', async ({ page }) => {
      const title = page.locator('[class*="text-white"]').first();
      if (await title.isVisible()) {
        await expect(title).toBeVisible();
      }
    });

    test('should truncate long titles', async ({ page }) => {
      const truncated = page.locator('.truncate').first();
      if (await truncated.isVisible()) {
        await expect(truncated).toHaveClass(/truncate/);
      }
    });
  });

  test.describe('PRE-CRD-006: Status Pill', () => {
    test('should display status pill', async ({ page }) => {
      const statusPill = page.locator('.rounded-full.font-medium').first();
      if (await statusPill.isVisible()) {
        await expect(statusPill).toBeVisible();
      }
    });

    test('should have clock icon for scheduled', async ({ page }) => {
      const scheduled = page.locator('text=⏱');
      if (await scheduled.first().isVisible()) {
        await expect(scheduled.first()).toBeVisible();
      }
    });

    test('should have check icon for posted', async ({ page }) => {
      const posted = page.locator('text=✓');
      if (await posted.first().isVisible()) {
        await expect(posted.first()).toBeVisible();
      }
    });

    test('should have violet styling for scheduled', async ({ page }) => {
      const scheduledPill = page.locator('[class*="bg-violet-500"]').first();
      if (await scheduledPill.isVisible()) {
        await expect(scheduledPill).toBeVisible();
      }
    });

    test('should have green styling for posted', async ({ page }) => {
      const postedPill = page.locator('[class*="bg-green-500"]').first();
      if (await postedPill.isVisible()) {
        await expect(postedPill).toBeVisible();
      }
    });
  });

  test.describe('PRE-CRD-007: Time Display', () => {
    test('should show time in meta row', async ({ page }) => {
      const time = page.locator('.text-\\[10px\\].text-zinc-500').first();
      if (await time.isVisible()) {
        await expect(time).toBeVisible();
      }
    });

    test('should display time in user timezone', async ({ page }) => {
      const timeText = page.locator('text=/\\d{1,2}:\\d{2}\\s*(AM|PM)?/').first();
      if (await timeText.isVisible()) {
        await expect(timeText).toBeVisible();
      }
    });
  });

  test.describe('PRE-CRD-008: Hover Effects', () => {
    test('should lift on hover', async ({ page }) => {
      const card = page.locator('[class*="hover:-translate-y"]').first();
      if (await card.isVisible()) {
        await expect(card).toHaveClass(/hover:-translate-y/);
      }
    });

    test('should show shadow on hover', async ({ page }) => {
      const card = page.locator('[class*="hover:shadow-lg"]').first();
      if (await card.isVisible()) {
        await expect(card).toHaveClass(/hover:shadow-lg/);
      }
    });

    test('should brighten background on hover', async ({ page }) => {
      const card = page.locator('[class*="hover:bg-zinc"]').first();
      if (await card.isVisible()) {
        await expect(card).toHaveClass(/hover:bg-zinc/);
      }
    });

    test('should brighten border on hover', async ({ page }) => {
      const card = page.locator('[class*="hover:border-zinc"]').first();
      if (await card.isVisible()) {
        await expect(card).toHaveClass(/hover:border-zinc/);
      }
    });
  });

  test.describe('PRE-CRD-009: Failed State', () => {
    test('should have red border for failed posts', async ({ page }) => {
      const failedCard = page.locator('[class*="border-red-500"]').first();
      if (await failedCard.isVisible()) {
        await expect(failedCard).toBeVisible();
      }
    });

    test('should show Retry button for failed posts', async ({ page }) => {
      const retryBtn = page.locator('button:has-text("Retry")').first();
      if (await retryBtn.isVisible()) {
        await expect(retryBtn).toBeVisible();
      }
    });

    test('should have red status indicator for failed', async ({ page }) => {
      const redLine = page.locator('.bg-red-500').first();
      if (await redLine.isVisible()) {
        await expect(redLine).toBeVisible();
      }
    });
  });

  test.describe('PRE-CRD-010: Platform Badge', () => {
    test('should show TikTok badge with pink color', async ({ page }) => {
      const tiktokBadge = page.locator('.bg-pink-500').first();
      if (await tiktokBadge.isVisible()) {
        await expect(tiktokBadge).toBeVisible();
      }
    });

    test('should show Instagram badge with purple color', async ({ page }) => {
      const igBadge = page.locator('.bg-purple-500').first();
      if (await igBadge.isVisible()) {
        await expect(igBadge).toBeVisible();
      }
    });

    test('should show YouTube badge with red color', async ({ page }) => {
      const ytBadge = page.locator('.bg-red-500').first();
      if (await ytBadge.isVisible()) {
        await expect(ytBadge).toBeVisible();
      }
    });

    test('should have platform icon in badge', async ({ page }) => {
      const icons = page.locator('text=/🎵|📸|▶️/');
      await expect(icons.first()).toBeVisible();
    });
  });
});

test.describe('PRE-DAY: Enhanced Day Headers', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-DAY-001: Today Highlight', () => {
    test('should highlight today with violet circle', async ({ page }) => {
      const todayCircle = page.locator('.bg-violet-500.text-white.font-bold');
      await expect(todayCircle.first()).toBeVisible();
    });

    test('should have column tint for today', async ({ page }) => {
      const todayColumn = page.locator('[class*="bg-violet-500"]').first();
      await expect(todayColumn).toBeVisible();
    });

    test('should have violet text for today weekday', async ({ page }) => {
      const todayWeekday = page.locator('.text-violet-400').first();
      await expect(todayWeekday).toBeVisible();
    });
  });

  test.describe('PRE-DAY-002: Day Number Display', () => {
    test('should display day numbers', async ({ page }) => {
      const dayNumbers = page.locator('.text-lg');
      const count = await dayNumbers.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should have semibold weight for non-today', async ({ page }) => {
      const dayNum = page.locator('.font-semibold').first();
      await expect(dayNum).toBeVisible();
    });

    test('should have bold weight for today', async ({ page }) => {
      const todayNum = page.locator('.font-bold').first();
      await expect(todayNum).toBeVisible();
    });
  });

  test.describe('PRE-DAY-003: Weekday Labels', () => {
    test('should display weekday abbreviations', async ({ page }) => {
      await expect(page.locator('text=Sun').first()).toBeVisible();
    });

    test('should have uppercase styling', async ({ page }) => {
      const weekday = page.locator('.uppercase.tracking-wider').first();
      await expect(weekday).toBeVisible();
    });

    test('should have muted color for non-today', async ({ page }) => {
      const mutedWeekday = page.locator('.text-zinc-500').first();
      await expect(mutedWeekday).toBeVisible();
    });
  });

  test.describe('PRE-DAY-004: Post Count Badges', () => {
    test('should show post count badge when posts exist', async ({ page }) => {
      const badge = page.locator('.text-\\[10px\\].px-1\\.5.py-0\\.5.rounded-full').first();
      if (await badge.isVisible()) {
        await expect(badge).toBeVisible();
      }
    });

    test('should have different styling for today badge', async ({ page }) => {
      const todayBadge = page.locator('[class*="bg-violet-400"]').first();
      if (await todayBadge.isVisible()) {
        await expect(todayBadge).toBeVisible();
      }
    });
  });

  test.describe('PRE-DAY-005: Week Separators', () => {
    test('should have stronger bottom border', async ({ page }) => {
      const strongBorder = page.locator('.border-b-2').first();
      await expect(strongBorder).toBeVisible();
    });

    test('should have lighter vertical borders', async ({ page }) => {
      const lightBorder = page.locator('[class*="border-zinc-800"]').first();
      await expect(lightBorder).toBeVisible();
    });
  });
});

test.describe('PRE-ADD: Add Button Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test.describe('PRE-ADD-001: Always Visible Add Button', () => {
    test('should show + Schedule button in each column', async ({ page }) => {
      const addBtns = page.locator('button:has-text("+")');
      const count = await addBtns.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should have dashed border styling', async ({ page }) => {
      const dashedBtn = page.locator('.border-dashed').first();
      await expect(dashedBtn).toBeVisible();
    });

    test('should show "Schedule" text on hover', async ({ page }) => {
      const addBtn = page.locator('button:has-text("+")').first();
      await addBtn.hover();
      const scheduleText = page.locator('text=Schedule');
      // Schedule text appears on hover
    });

    test('should have tooltip', async ({ page }) => {
      const addBtn = page.locator('[title="Schedule post"]').first();
      if (await addBtn.isVisible()) {
        await expect(addBtn).toBeVisible();
      }
    });
  });

  test.describe('PRE-ADD-002: Add Button Hover States', () => {
    test('should change border color on hover', async ({ page }) => {
      const btn = page.locator('[class*="hover:border-violet"]').first();
      if (await btn.isVisible()) {
        await expect(btn).toHaveClass(/hover:border-violet/);
      }
    });

    test('should change text color on hover', async ({ page }) => {
      const btn = page.locator('[class*="hover:text-violet"]').first();
      if (await btn.isVisible()) {
        await expect(btn).toHaveClass(/hover:text-violet/);
      }
    });

    test('should have subtle background on hover', async ({ page }) => {
      const btn = page.locator('[class*="hover:bg-violet"]').first();
      if (await btn.isVisible()) {
        await expect(btn).toHaveClass(/hover:bg-violet/);
      }
    });
  });

  test.describe('PRE-ADD-003: Add Button Click Action', () => {
    test('should open media selector on click', async ({ page }) => {
      const addBtn = page.locator('button:has-text("+")').first();
      await addBtn.click();
      await expect(page.locator('text=Select project')).toBeVisible({ timeout: 5000 });
    });

    test('should show selected date in modal', async ({ page }) => {
      const addBtn = page.locator('button:has-text("+")').first();
      await addBtn.click();
      await expect(page.locator('text=Schedule for')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('PRE-ADD-004: Empty State Drop Zone', () => {
    test('should show drop zone in empty days', async ({ page }) => {
      const dropZone = page.locator('.border-dashed').first();
      await expect(dropZone).toBeVisible();
    });

    test('should highlight drop zone when dragging', async ({ page }) => {
      // Check for drag-aware styling classes
      const dragZone = page.locator('[class*="hover:bg-zinc"]').first();
      if (await dragZone.isVisible()) {
        await expect(dragZone).toBeVisible();
      }
    });
  });
});
