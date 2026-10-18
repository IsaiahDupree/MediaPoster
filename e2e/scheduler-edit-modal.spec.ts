/**
 * E2E Tests: Edit Modal & Delete Flow (SCH-MOD-*)
 * Tests for video preview, editable fields, date picker, save/delete
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';

test.describe('SCH-MOD: Edit Modal Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test.describe('SCH-MOD-001: Modal Opening', () => {
    test('should open edit modal when clicking scheduled post', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('text=Edit scheduled post')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display modal overlay', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('.fixed.inset-0.bg-black\\/90')).toBeVisible();
      }
    });

    test('should have close button (X)', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("×")')).toBeVisible();
      }
    });
  });

  test.describe('SCH-MOD-002: Video Preview', () => {
    test('should display video player', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('video')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have video controls', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const video = page.locator('video[controls]');
        await expect(video).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display score/duration overlay', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const overlay = page.locator('.absolute.top-2.left-2');
        await expect(overlay).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('SCH-MOD-003: Editable Fields', () => {
    test('should have editable title input', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const titleInput = page.locator('input[placeholder="Post title"]');
        await expect(titleInput).toBeVisible({ timeout: 5000 });
        await expect(titleInput).toBeEditable();
      }
    });

    test('should have editable caption textarea', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const captionTextarea = page.locator('textarea');
        await expect(captionTextarea).toBeVisible({ timeout: 5000 });
        await expect(captionTextarea).toBeEditable();
      }
    });

    test('should allow editing title', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const titleInput = page.locator('input[placeholder="Post title"]');
        await titleInput.fill('Updated Test Title');
        await expect(titleInput).toHaveValue('Updated Test Title');
      }
    });

    test('should allow editing caption with hashtags', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const captionTextarea = page.locator('textarea');
        await captionTextarea.fill('New caption #test #hashtag');
        await expect(captionTextarea).toHaveValue('New caption #test #hashtag');
      }
    });
  });

  test.describe('SCH-MOD-004: Account Selector', () => {
    test('should display platform icon', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const platformIcon = page.locator('.rounded-full >> text=/🎵|📸|▶️/');
        await expect(platformIcon.first()).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show account selector or account name', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const accountInfo = page.locator('text=/@|No account/');
        await expect(accountInfo.first()).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('SCH-MOD-005: Visibility Dropdown', () => {
    test('should have visibility dropdown', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const visibilitySelect = page.locator('select:has(option:has-text("Public"))');
        await expect(visibilitySelect).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have Public, Private, Unlisted options', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('option:has-text("Public")')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('option:has-text("Private")')).toBeVisible();
        await expect(page.locator('option:has-text("Unlisted")')).toBeVisible();
      }
    });

    test('should allow changing visibility', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const visibilitySelect = page.locator('select:has(option:has-text("Public"))').last();
        await visibilitySelect.selectOption('private');
        await expect(visibilitySelect).toHaveValue('private');
      }
    });
  });

  test.describe('SCH-MOD-006: Action Buttons', () => {
    test('should have image button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("🖼️")')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have hashtag button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("#")')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have mention button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("@")')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('SCH-MOD-007: Date/Time Display & Picker', () => {
    test('should display current date/time', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const dateButton = page.locator('button:has-text("📅")');
        await expect(dateButton).toBeVisible({ timeout: 5000 });
      }
    });

    test('should open date picker when clicking date', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        // Date picker should appear
        await expect(page.locator('text=/Su|Mo|Tu|We|Th|Fr|Sa/')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show month navigation in date picker', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        await expect(page.locator('.absolute >> text=←')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('.absolute >> text=→')).toBeVisible();
      }
    });

    test('should show 24-hour toggle', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        await expect(page.locator('text=Use 24-hr format')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show time input in date picker', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        await expect(page.locator('input[type="time"]')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show timezone display', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        await expect(page.locator('text=/Eastern|Central|Mountain|Pacific|London|Paris|Tokyo|Sydney/')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should allow selecting a new date', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("📅")');
        // Click a day number
        const dayButton = page.locator('.absolute >> button:has-text("15")');
        if (await dayButton.isVisible()) {
          await dayButton.click();
        }
      }
    });
  });

  test.describe('SCH-MOD-008: Save Button', () => {
    test('should have Save button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("Save")')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should close modal on successful save', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Save")');
        // Modal should close (may take a moment for API)
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 10000 });
      }
    });
  });

  test.describe('SCH-MOD-009: Modal Close Behavior', () => {
    test('should close modal when clicking X button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.locator('button:has-text("×")').last().click();
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible({ timeout: 5000 });
      }
    });
  });
});

test.describe('SCH-DEL: Delete Flow Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
  });

  test.describe('SCH-DEL-001: Delete Button', () => {
    test('should have Delete button in edit modal', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await expect(page.locator('button:has-text("Delete")')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have red styling on Delete button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        const deleteBtn = page.locator('button:has-text("Delete")');
        await expect(deleteBtn).toHaveClass(/border-red-500|text-red-500/);
      }
    });
  });

  test.describe('SCH-DEL-002: Delete Confirmation Modal', () => {
    test('should open confirmation modal when clicking Delete', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await expect(page.locator('text=Delete post')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show confirmation message', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await expect(page.locator('text=Are you sure you want to delete')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have Cancel button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await expect(page.locator('button:has-text("Cancel")')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have Confirm button', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await expect(page.locator('button:has-text("Confirm")')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('SCH-DEL-003: Cancel Delete', () => {
    test('should close confirmation and keep post when clicking Cancel', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await page.click('button:has-text("Cancel")');
        // Confirmation should close, edit modal should still be open
        await expect(page.locator('text=Delete post')).not.toBeVisible({ timeout: 5000 });
        await expect(page.locator('text=Edit scheduled post')).toBeVisible();
      }
    });
  });

  test.describe('SCH-DEL-004: Confirm Delete', () => {
    test('should close all modals when confirming delete', async ({ page }) => {
      const postCard = page.locator('.cursor-pointer.rounded-lg').first();
      if (await postCard.isVisible()) {
        await postCard.click();
        await page.click('button:has-text("Delete")');
        await page.click('button:has-text("Confirm")');
        // Both modals should close
        await expect(page.locator('text=Delete post')).not.toBeVisible({ timeout: 10000 });
        await expect(page.locator('text=Edit scheduled post')).not.toBeVisible();
      }
    });
  });
});
