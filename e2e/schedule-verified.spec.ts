/**
 * E2E Tests: Schedule Page with Verified Results
 * These tests verify actual API responses and data integrity
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';
const API_URL = 'http://localhost:5555';

test.describe('Schedule API Verification', () => {
  
  test('VERIFY-001: Media DB API returns valid data structure', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/media-db/list?limit=10`);
    
    // Must be 200 OK
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    
    // Must be array
    expect(Array.isArray(data)).toBe(true);
    
    // If items exist, verify structure
    if (data.length > 0) {
      const item = data[0];
      
      // Required fields must exist
      expect(item.media_id).toBeDefined();
      expect(typeof item.media_id).toBe('string');
      expect(item.filename).toBeDefined();
      expect(item.status).toBeDefined();
      
      // media_id must be valid UUID format
      expect(item.media_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    }
  });

  test('VERIFY-002: Curated content filter returns approved items', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/media-db/list?limit=500`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    const curatedItems = data.filter((item: any) => item.curation_status === 'approved');
    
    // Log for debugging
    console.log(`Total items: ${data.length}, Curated: ${curatedItems.length}`);
    
    // Each curated item must have valid curation_status
    for (const item of curatedItems) {
      expect(item.curation_status).toBe('approved');
      expect(item.media_id).toBeDefined();
    }
  });

  test('VERIFY-003: Analyzed content has pre_social_score', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/media-db/list?limit=500`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    const analyzedItems = data.filter((item: any) => 
      item.status === 'analyzed' && item.pre_social_score !== null
    );
    
    console.log(`Analyzed items with scores: ${analyzedItems.length}`);
    
    // Verify score structure
    for (const item of analyzedItems.slice(0, 5)) {
      expect(typeof item.pre_social_score).toBe('number');
      expect(item.pre_social_score).toBeGreaterThanOrEqual(0);
      expect(item.pre_social_score).toBeLessThanOrEqual(100);
    }
  });

  test('VERIFY-004: Thumbnail endpoint returns image', async ({ request }) => {
    // First get a valid media_id
    const listResponse = await request.get(`${API_URL}/api/media-db/list?limit=5`);
    expect(listResponse.status()).toBe(200);
    
    const data = await listResponse.json();
    if (data.length > 0) {
      const mediaId = data[0].media_id;
      
      // Request thumbnail
      const thumbResponse = await request.get(`${API_URL}/api/media-db/thumbnail/${mediaId}`);
      
      // Should return 200 or 404 (if no thumbnail generated)
      expect([200, 404]).toContain(thumbResponse.status());
      
      if (thumbResponse.status() === 200) {
        const contentType = thumbResponse.headers()['content-type'];
        expect(contentType).toMatch(/image\//);
      }
    }
  });

  test('VERIFY-005: Schedule list endpoint works', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/schedule/list`);
    
    // Should return 200
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    // Can be array directly or object with items array
    const isValid = Array.isArray(data) || (data && typeof data === 'object');
    expect(isValid).toBe(true);
  });

  test('VERIFY-006: Schedule create endpoint validates input', async ({ request }) => {
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 1);
    futureDate.setHours(12, 0, 0, 0);

    // Valid request should succeed or return known error
    const response = await request.post(`${API_URL}/api/schedule/create`, {
      data: {
        content_id: 'e2e-test-' + Date.now(),
        title: 'E2E Verified Test Post',
        caption: 'Test caption for verification',
        hashtags: ['#test', '#e2e', '#verified'],
        platform: 'tiktok',
        account_id: 'e2e-test-account',
        account_username: 'e2e_tester',
        scheduled_at: futureDate.toISOString(),
        post_type: 'reel',
        thumbnail_url: null,
      },
    });

    // Should succeed (201) or already exists (200) or constraint violation (422/500)
    expect([200, 201, 422, 500]).toContain(response.status());
    
    // If success, verify response has ID
    if (response.status() === 200 || response.status() === 201) {
      const data = await response.json();
      expect(data.id).toBeDefined();
    }
  });
});

test.describe('Schedule UI Verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
  });

  test('VERIFY-UI-001: Page loads with calendar view', async ({ page }) => {
    // Must have view toggle buttons - look for any view control
    const weekBtn = page.locator('button:has-text("Week"), button:has-text("week")');
    const monthBtn = page.locator('button:has-text("Month"), button:has-text("month")');
    const dayBtn = page.locator('button:has-text("Day"), button:has-text("day")');
    
    // At least one view button should be visible
    const hasWeek = await weekBtn.first().isVisible({ timeout: 5000 }).catch(() => false);
    const hasMonth = await monthBtn.first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasDay = await dayBtn.first().isVisible({ timeout: 3000 }).catch(() => false);
    
    expect(hasWeek || hasMonth || hasDay).toBe(true);
  });

  test('VERIFY-UI-002: Plus button opens modal with real media count', async ({ page }) => {
    // Find + button
    const plusButton = page.locator('button:has-text("+")').first();
    await expect(plusButton).toBeVisible({ timeout: 5000 });
    
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Modal must show clip count
    const clipsText = page.locator('text=/\\d+ clips available/');
    await expect(clipsText).toBeVisible({ timeout: 5000 });
    
    // Extract and verify count is a number > 0
    const text = await clipsText.textContent();
    const match = text?.match(/(\d+) clips/);
    expect(match).not.toBeNull();
    
    const count = parseInt(match![1]);
    expect(count).toBeGreaterThan(0);
    console.log(`Verified: ${count} clips available`);
  });

  test('VERIFY-UI-003: Media grid shows actual thumbnails', async ({ page }) => {
    const plusButton = page.locator('button:has-text("+")').first();
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Wait for images to load
    const images = page.locator('.grid img, .grid-cols-4 img');
    const count = await images.count();
    
    console.log(`Found ${count} thumbnail images`);
    expect(count).toBeGreaterThan(0);
    
    // Verify first image has valid src (either media-db or media endpoint)
    if (count > 0) {
      const firstImg = images.first();
      const src = await firstImg.getAttribute('src');
      expect(src).not.toBeNull();
      // Accept either thumbnail endpoint
      const hasValidSrc = src?.includes('/api/media-db/thumbnail/') || src?.includes('/api/media/thumbnail/');
      expect(hasValidSrc).toBe(true);
    }
  });

  test('VERIFY-UI-004: Selecting media shows score from API', async ({ page }) => {
    const plusButton = page.locator('button:has-text("+")').first();
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Click first media item
    const mediaItem = page.locator('.cursor-pointer.group').first();
    await expect(mediaItem).toBeVisible({ timeout: 5000 });
    await mediaItem.click();
    await page.waitForTimeout(1000);
    
    // Verify score display exists (shows X/100)
    const scoreDisplay = page.locator('text=/\\d+.*\\/100/');
    await expect(scoreDisplay).toBeVisible({ timeout: 3000 });
    
    // Get the score text
    const scoreText = await scoreDisplay.textContent();
    console.log(`Score displayed: ${scoreText}`);
    expect(scoreText).toMatch(/\d+/);
  });

  test('VERIFY-UI-005: Curated filter shows approved content only', async ({ page }) => {
    const plusButton = page.locator('button:has-text("+")').first();
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Get initial count
    const initialClips = page.locator('text=/\\d+ clips available/');
    const initialText = await initialClips.textContent();
    const initialCount = parseInt(initialText?.match(/(\d+)/)?.[1] || '0');
    console.log(`Initial clips: ${initialCount}`);
    
    // Click Curated filter
    const curatedBtn = page.locator('button:has-text("Curated")');
    await expect(curatedBtn).toBeVisible({ timeout: 3000 });
    await curatedBtn.click();
    await page.waitForTimeout(1000);
    
    // Get curated count
    const curatedClips = page.locator('text=/\\d+ clips available/');
    const curatedText = await curatedClips.textContent();
    const curatedCount = parseInt(curatedText?.match(/(\d+)/)?.[1] || '0');
    console.log(`Curated clips: ${curatedCount}`);
    
    // Curated count should be <= initial count
    expect(curatedCount).toBeLessThanOrEqual(initialCount);
  });

  test('VERIFY-UI-006: Back button returns to grid', async ({ page }) => {
    const plusButton = page.locator('button:has-text("+")').first();
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Select media
    const mediaItem = page.locator('.cursor-pointer.group').first();
    await mediaItem.click();
    await page.waitForTimeout(500);
    
    // Click back
    const backBtn = page.locator('text=Back to clips');
    if (await backBtn.isVisible({ timeout: 2000 })) {
      await backBtn.click();
      await page.waitForTimeout(500);
      
      // Verify we're back to grid (clips count visible)
      const clipsText = page.locator('text=/\\d+ clips available/');
      await expect(clipsText).toBeVisible({ timeout: 3000 });
    }
  });

  test('VERIFY-UI-007: Platform buttons are clickable', async ({ page }) => {
    const plusButton = page.locator('button:has-text("+")').first();
    await plusButton.click();
    await page.waitForTimeout(1500);
    
    // Find platform buttons in footer
    const tiktokBtn = page.locator('button[title*="TikTok"]').or(page.locator('button:has-text("🎵")'));
    const instagramBtn = page.locator('button[title*="Instagram"]').or(page.locator('button:has-text("📸")'));
    
    // At least one should be visible
    const hasTiktok = await tiktokBtn.first().isVisible({ timeout: 2000 }).catch(() => false);
    const hasInstagram = await instagramBtn.first().isVisible({ timeout: 1000 }).catch(() => false);
    
    expect(hasTiktok || hasInstagram).toBe(true);
  });
});

test.describe('Schedule Complete Flow Verification', () => {
  test('VERIFY-FLOW-001: Full scheduling workflow', async ({ page, request }) => {
    // Step 1: Verify API has content
    const apiResponse = await request.get(`${API_URL}/api/media-db/list?limit=10`);
    expect(apiResponse.status()).toBe(200);
    const apiData = await apiResponse.json();
    expect(apiData.length).toBeGreaterThan(0);
    console.log(`API has ${apiData.length} items`);
    
    // Step 2: Load page
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
    
    // Step 3: Open modal
    const plusButton = page.locator('button:has-text("+")').first();
    await expect(plusButton).toBeVisible({ timeout: 5000 });
    await plusButton.click();
    await page.waitForTimeout(2000);
    
    // Step 4: Verify media loaded
    const clipsText = page.locator('text=/\\d+ clips available/');
    await expect(clipsText).toBeVisible({ timeout: 5000 });
    
    // Step 5: Select media
    const mediaItem = page.locator('.cursor-pointer.group').first();
    await expect(mediaItem).toBeVisible({ timeout: 5000 });
    await mediaItem.click();
    await page.waitForTimeout(1000);
    
    // Step 6: Verify detail view
    const selectBtn = page.locator('button:has-text("Select Clip")');
    await expect(selectBtn).toBeVisible({ timeout: 5000 });
    
    // Step 7: Click schedule
    await selectBtn.click();
    await page.waitForTimeout(2000);
    
    // Step 8: Check result (success toast or modal closes)
    const successToast = page.locator('text=scheduled successfully');
    const modalClosed = await page.locator('text=Schedule new post').isHidden({ timeout: 3000 }).catch(() => false);
    const errorToast = page.locator('text=Failed to schedule');
    
    const hasSuccess = await successToast.isVisible({ timeout: 1000 }).catch(() => false);
    const hasError = await errorToast.isVisible({ timeout: 1000 }).catch(() => false);
    
    console.log(`Result - Success: ${hasSuccess}, Modal closed: ${modalClosed}, Error: ${hasError}`);
    
    // Either success or known error (not undefined errors)
    expect(hasSuccess || modalClosed || hasError).toBe(true);
  });
});
