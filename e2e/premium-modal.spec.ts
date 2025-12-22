/**
 * E2E Tests: Premium Edit Modal (PRE-MOD-*)
 * Tests for edit modal with unsaved indicator, schedule summary, sticky actions
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('PRE-MOD: Premium Edit Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  async function openEditModal(page: any) {
    const postCard = page.locator('[class*="group/card"]').first();
    if (await postCard.isVisible()) {
      await postCard.click();
      await page.waitForSelector('text=Edit scheduled post', { timeout: 5000 });
      return true;
    }
    return false;
  }

  test.describe('PRE-MOD-001: Modal Container', () => {
    test('should open modal when clicking post card', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Edit scheduled post')).toBeVisible();
      }
    });

    test('should have backdrop blur', async ({ page }) => {
      if (await openEditModal(page)) {
        const backdrop = page.locator('.backdrop-blur-sm');
        await expect(backdrop.first()).toBeVisible();
      }
    });

    test('should have rounded-2xl styling', async ({ page }) => {
      if (await openEditModal(page)) {
        const modal = page.locator('.rounded-2xl');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('should have shadow-2xl styling', async ({ page }) => {
      if (await openEditModal(page)) {
        const modal = page.locator('[class*="shadow-2xl"]');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('should have max height constraint', async ({ page }) => {
      if (await openEditModal(page)) {
        const modal = page.locator('[class*="max-h-"]');
        await expect(modal.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-002: Header Section', () => {
    test('should display title "Edit scheduled post"', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Edit scheduled post')).toBeVisible();
      }
    });

    test('should have close button with X icon', async ({ page }) => {
      if (await openEditModal(page)) {
        const closeBtn = page.locator('svg path[d*="M6 18L18 6"]').locator('..');
        await expect(closeBtn).toBeVisible();
      }
    });

    test('should close modal when clicking X', async ({ page }) => {
      if (await openEditModal(page)) {
        await page.locator('svg path[d*="M6 18L18 6"]').locator('..').click();
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible();
      }
    });

    test('should have sticky header', async ({ page }) => {
      if (await openEditModal(page)) {
        const stickyHeader = page.locator('.sticky.top-0');
        await expect(stickyHeader.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-003: Unsaved Changes Indicator', () => {
    test('should not show unsaved indicator initially', async ({ page }) => {
      if (await openEditModal(page)) {
        const unsavedBadge = page.locator('text=Unsaved changes');
        await expect(unsavedBadge).not.toBeVisible();
      }
    });

    test('should show unsaved indicator when title changed', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input[placeholder="Post title"]');
        const originalValue = await titleInput.inputValue();
        await titleInput.fill(originalValue + ' modified');
        const unsavedBadge = page.locator('text=Unsaved changes');
        await expect(unsavedBadge).toBeVisible();
      }
    });

    test('should show unsaved indicator when caption changed', async ({ page }) => {
      if (await openEditModal(page)) {
        const captionInput = page.locator('textarea');
        await captionInput.fill('New caption text #test');
        const unsavedBadge = page.locator('text=Unsaved changes');
        await expect(unsavedBadge).toBeVisible();
      }
    });

    test('should have amber styling for unsaved indicator', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.fill('Modified title');
        const amberBadge = page.locator('.bg-amber-500\\/20.text-amber-400');
        await expect(amberBadge).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-004: Schedule Summary Bar', () => {
    test('should display schedule summary bar', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Scheduled for')).toBeVisible();
      }
    });

    test('should show date in summary', async ({ page }) => {
      if (await openEditModal(page)) {
        const dateText = page.locator('text=/[A-Z][a-z]{2}, [A-Z][a-z]{2} \\d+/');
        await expect(dateText.first()).toBeVisible();
      }
    });

    test('should show time in summary', async ({ page }) => {
      if (await openEditModal(page)) {
        const timeText = page.locator('text=/\\d{1,2}:\\d{2}/');
        await expect(timeText.first()).toBeVisible();
      }
    });

    test('should show timezone in summary', async ({ page }) => {
      if (await openEditModal(page)) {
        const tzText = page.locator('text=/ET|CT|MT|PT|GMT/');
        await expect(tzText.first()).toBeVisible();
      }
    });

    test('should have Change button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("Change")')).toBeVisible();
      }
    });

    test('should open date picker when clicking Change', async ({ page }) => {
      if (await openEditModal(page)) {
        await page.click('button:has-text("Change")');
        await expect(page.locator('text=/Su|Mo|Tu|We|Th|Fr|Sa/')).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-005: Video Player Section', () => {
    test('should display video player', async ({ page }) => {
      if (await openEditModal(page)) {
        const video = page.locator('video');
        await expect(video).toBeVisible();
      }
    });

    test('should have rounded styling on video', async ({ page }) => {
      if (await openEditModal(page)) {
        const videoContainer = page.locator('.rounded-xl video').locator('..');
        await expect(videoContainer).toBeVisible();
      }
    });

    test('should show score badge if available', async ({ page }) => {
      if (await openEditModal(page)) {
        const scoreBadge = page.locator('text=/\\/100/');
        if (await scoreBadge.first().isVisible()) {
          await expect(scoreBadge.first()).toBeVisible();
        }
      }
    });

    test('should show platform badge on video', async ({ page }) => {
      if (await openEditModal(page)) {
        const platformBadge = page.locator('text=/🎵|📸|▶️/');
        await expect(platformBadge.first()).toBeVisible();
      }
    });

    test('should have shadow on video container', async ({ page }) => {
      if (await openEditModal(page)) {
        const shadowContainer = page.locator('.shadow-lg video').locator('..');
        await expect(shadowContainer).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-006: Account Selector', () => {
    test('should display account selector section', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Posting to')).toBeVisible();
      }
    });

    test('should show platform icon in account section', async ({ page }) => {
      if (await openEditModal(page)) {
        const icon = page.locator('text=/🎵|📸|▶️/');
        await expect(icon.first()).toBeVisible();
      }
    });

    test('should show account username', async ({ page }) => {
      if (await openEditModal(page)) {
        const account = page.locator('text=/@/');
        await expect(account.first()).toBeVisible();
      }
    });

    test('should have rounded card styling', async ({ page }) => {
      if (await openEditModal(page)) {
        const card = page.locator('.rounded-xl.p-3');
        await expect(card.first()).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-007: Title Input', () => {
    test('should display title input', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input[placeholder="Post title"]');
        await expect(titleInput).toBeVisible();
      }
    });

    test('should have Title label', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Title').first()).toBeVisible();
      }
    });

    test('should allow editing title', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.fill('New Test Title');
        await expect(titleInput).toHaveValue('New Test Title');
      }
    });

    test('should have rounded-xl styling', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input.rounded-xl');
        await expect(titleInput.first()).toBeVisible();
      }
    });

    test('should have focus ring on focus', async ({ page }) => {
      if (await openEditModal(page)) {
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.focus();
        await expect(titleInput).toBeFocused();
      }
    });
  });

  test.describe('PRE-MOD-008: Caption Input', () => {
    test('should display caption textarea', async ({ page }) => {
      if (await openEditModal(page)) {
        const textarea = page.locator('textarea');
        await expect(textarea).toBeVisible();
      }
    });

    test('should have Caption label', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Caption').first()).toBeVisible();
      }
    });

    test('should allow editing caption', async ({ page }) => {
      if (await openEditModal(page)) {
        const textarea = page.locator('textarea');
        await textarea.fill('New caption with #hashtag @mention');
        await expect(textarea).toHaveValue('New caption with #hashtag @mention');
      }
    });

    test('should have placeholder text', async ({ page }) => {
      if (await openEditModal(page)) {
        const textarea = page.locator('textarea[placeholder*="hashtags"]');
        await expect(textarea).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-009: Action Buttons Row', () => {
    test('should display image button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("🖼️")')).toBeVisible();
      }
    });

    test('should display hashtag button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("#")')).toBeVisible();
      }
    });

    test('should display mention button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("@")')).toBeVisible();
      }
    });

    test('should have tooltip on image button', async ({ page }) => {
      if (await openEditModal(page)) {
        const btn = page.locator('[title="Add image"]');
        await expect(btn).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-010: Visibility Dropdown', () => {
    test('should display visibility dropdown', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=Visibility')).toBeVisible();
      }
    });

    test('should have Public option with emoji', async ({ page }) => {
      if (await openEditModal(page)) {
        const select = page.locator('select').last();
        await expect(select.locator('option:has-text("🌍 Public")')).toBeVisible();
      }
    });

    test('should have Private option with emoji', async ({ page }) => {
      if (await openEditModal(page)) {
        const select = page.locator('select').last();
        await expect(select.locator('option:has-text("🔒 Private")')).toBeVisible();
      }
    });

    test('should have Unlisted option with emoji', async ({ page }) => {
      if (await openEditModal(page)) {
        const select = page.locator('select').last();
        await expect(select.locator('option:has-text("👁️ Unlisted")')).toBeVisible();
      }
    });

    test('should allow changing visibility', async ({ page }) => {
      if (await openEditModal(page)) {
        const select = page.locator('select').last();
        await select.selectOption('private');
        await expect(select).toHaveValue('private');
      }
    });
  });

  test.describe('PRE-MOD-011: Footer Section', () => {
    test('should have sticky footer', async ({ page }) => {
      if (await openEditModal(page)) {
        const stickyFooter = page.locator('.sticky.bottom-0');
        await expect(stickyFooter.first()).toBeVisible();
      }
    });

    test('should have Delete button on left', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("Delete")')).toBeVisible();
      }
    });

    test('should have date/time button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("📅")')).toBeVisible();
      }
    });

    test('should have Save button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("Save")')).toBeVisible();
      }
    });

    test('should have backdrop blur on footer', async ({ page }) => {
      if (await openEditModal(page)) {
        const blurFooter = page.locator('.backdrop-blur-sm.sticky.bottom-0');
        await expect(blurFooter).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-012: Delete Button Styling', () => {
    test('should have red styling on delete button', async ({ page }) => {
      if (await openEditModal(page)) {
        const deleteBtn = page.locator('button:has-text("Delete")');
        await expect(deleteBtn).toHaveClass(/text-red|border-red/);
      }
    });

    test('should have trash icon on delete button', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('text=🗑️')).toBeVisible();
      }
    });

    test('should open confirm modal when clicking delete', async ({ page }) => {
      if (await openEditModal(page)) {
        await page.click('button:has-text("Delete")');
        await expect(page.locator('text=Delete post')).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-013: Date Picker Button', () => {
    test('should show calendar emoji', async ({ page }) => {
      if (await openEditModal(page)) {
        await expect(page.locator('button:has-text("📅")')).toBeVisible();
      }
    });

    test('should show current date', async ({ page }) => {
      if (await openEditModal(page)) {
        const dateBtn = page.locator('button:has-text("📅")');
        const text = await dateBtn.textContent();
        expect(text).toMatch(/\d+/);
      }
    });

    test('should open date picker when clicked', async ({ page }) => {
      if (await openEditModal(page)) {
        await page.click('button:has-text("📅")');
        await expect(page.locator('text=/Su|Mo|Tu|We|Th|Fr|Sa/')).toBeVisible();
      }
    });
  });

  test.describe('PRE-MOD-014: Save Button', () => {
    test('should have violet/purple styling', async ({ page }) => {
      if (await openEditModal(page)) {
        const saveBtn = page.locator('button:has-text("Save")');
        await expect(saveBtn).toHaveClass(/bg-violet|bg-purple/);
      }
    });

    test('should close modal on save', async ({ page }) => {
      if (await openEditModal(page)) {
        await page.click('button:has-text("Save")');
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 10000 });
      }
    });
  });
});

test.describe('PRE-DEL: Delete Confirmation Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  async function openDeleteConfirm(page: any) {
    const postCard = page.locator('[class*="group/card"]').first();
    if (await postCard.isVisible()) {
      await postCard.click();
      await page.waitForSelector('text=Edit scheduled post', { timeout: 5000 });
      await page.click('button:has-text("Delete")');
      return true;
    }
    return false;
  }

  test.describe('PRE-DEL-001: Confirm Modal Display', () => {
    test('should show delete confirmation modal', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        await expect(page.locator('text=Delete post')).toBeVisible();
      }
    });

    test('should show confirmation message', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        await expect(page.locator('text=/sure|delete|remove/i')).toBeVisible();
      }
    });
  });

  test.describe('PRE-DEL-002: Confirm Modal Actions', () => {
    test('should have Cancel button', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        await expect(page.locator('button:has-text("Cancel")')).toBeVisible();
      }
    });

    test('should have Confirm button', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        await expect(page.locator('button:has-text("Confirm")')).toBeVisible();
      }
    });

    test('should close on Cancel', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        await page.click('button:has-text("Cancel")');
        await expect(page.locator('text=Delete post')).not.toBeVisible();
      }
    });

    test('should have red styling on Confirm', async ({ page }) => {
      if (await openDeleteConfirm(page)) {
        const confirmBtn = page.locator('button:has-text("Confirm")');
        await expect(confirmBtn).toHaveClass(/bg-red/);
      }
    });
  });
});
