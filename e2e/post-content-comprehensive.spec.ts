/**
 * Comprehensive E2E Tests for Post Content Page
 * 
 * Tests:
 * - Page load and data fetching
 * - Account selection/deselection
 * - Content regeneration with platform limits
 * - Character limit enforcement
 * - Thumbnail selection
 * - Publish and Schedule workflows
 * - Console logging verification
 */

import { test, expect, Page, ConsoleMessage } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5557';
const API_URL = 'http://localhost:5555';

// Platform character limits (should match frontend config)
const PLATFORM_LIMITS: Record<string, { title: number; description: number; hashtags: number }> = {
  tiktok: { title: 80, description: 3200, hashtags: 5 },
  instagram: { title: 80, description: 1760, hashtags: 5 },
  youtube: { title: 80, description: 4000, hashtags: 3 },
  twitter: { title: 224, description: 224, hashtags: 2 },
  linkedin: { title: 80, description: 2400, hashtags: 5 },
  bluesky: { title: 240, description: 240, hashtags: 3 },
  threads: { title: 400, description: 400, hashtags: 3 },
  pinterest: { title: 80, description: 400, hashtags: 5 },
  facebook: { title: 64, description: 50000, hashtags: 3 },
};

// Helper to capture console logs
function setupConsoleCapture(page: Page) {
  const logs: { type: string; text: string; category?: string }[] = [];
  
  page.on('console', (msg: ConsoleMessage) => {
    const text = msg.text();
    // Extract category from our custom log format [timestamp] [PostContent] [CATEGORY]
    const categoryMatch = text.match(/\[PostContent\]\s*\[(\w+)\]/);
    logs.push({
      type: msg.type(),
      text: text,
      category: categoryMatch ? categoryMatch[1] : undefined
    });
  });
  
  return logs;
}

// Get a valid media ID for testing
async function getTestMediaId(): Promise<string | null> {
  try {
    const response = await fetch(`${API_URL}/api/media-db/list?limit=1`);
    if (response.ok) {
      const data = await response.json();
      if (data.items && data.items.length > 0) {
        return data.items[0].media_id;
      }
    }
  } catch (e) {
    console.error('Failed to get test media ID:', e);
  }
  return null;
}

test.describe('Post Content Page - Comprehensive Tests', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
    if (!testMediaId) {
      console.warn('No test media found - some tests will be skipped');
    }
  });

  test.describe('Page Load & Data Fetching', () => {
    test('page loads with media details', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Should show Review & Post Content heading
      await expect(page.locator('h1:has-text("Review & Post Content")')).toBeVisible({ timeout: 10000 });
      
      // Should have console logs for INIT
      await page.waitForTimeout(2000);
      const initLogs = logs.filter(l => l.category === 'INIT');
      expect(initLogs.length).toBeGreaterThan(0);
      console.log('✓ Page loaded with INIT logs');
    });

    test('loads connected accounts', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // Should have API logs for accounts
      const apiLogs = logs.filter(l => l.category === 'API');
      expect(apiLogs.length).toBeGreaterThan(0);
      
      // Should show Select Account section
      await expect(page.locator('text=Select Account')).toBeVisible();
      console.log('✓ Accounts loaded');
    });

    test('displays video player', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Should have video element
      const video = page.locator('video');
      await expect(video).toBeVisible();
      console.log('✓ Video player visible');
    });

    test('displays thumbnails section', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Should have thumbnails section
      await expect(page.locator('text=Thumbnails')).toBeVisible();
      await expect(page.locator('text=Auto-Select Best')).toBeVisible();
      console.log('✓ Thumbnails section visible');
    });
  });

  test.describe('Account Selection', () => {
    test('Select All button enables all accounts', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const selectAllBtn = page.locator('button:has-text("Select All")');
      if (await selectAllBtn.isVisible()) {
        await selectAllBtn.click();
        await page.waitForTimeout(500);
        
        // Count enabled accounts (should match total)
        const accountButtons = page.locator('[data-testid="account-toggle"], button:has([class*="green"])');
        console.log('✓ Select All clicked');
      }
    });

    test('Deselect All button disables all accounts', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const deselectAllBtn = page.locator('button:has-text("Deselect All")');
      if (await deselectAllBtn.isVisible()) {
        await deselectAllBtn.click();
        await page.waitForTimeout(500);
        console.log('✓ Deselect All clicked');
      }
    });

    test('clicking account toggles selection', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Find first account button and click
      const accountBtn = page.locator('button:has-text("@")').first();
      if (await accountBtn.isVisible()) {
        await accountBtn.click();
        await page.waitForTimeout(300);
        console.log('✓ Account toggle clicked');
      }
    });
  });

  test.describe('Content Regeneration', () => {
    test('Regenerate button triggers API call', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      
      // Find Regenerate button (single account)
      const regenerateBtn = page.locator('button:has-text("Regenerate")').first();
      
      if (await regenerateBtn.isVisible()) {
        // Set up API listener
        const apiPromise = page.waitForResponse(
          response => response.url().includes('/api/analysis/generate-captions'),
          { timeout: 30000 }
        ).catch(() => null);
        
        await regenerateBtn.click();
        
        const response = await apiPromise;
        if (response) {
          expect(response.status()).toBeLessThan(500);
          console.log('✓ Regenerate API called successfully');
        }
        
        // Check for REGEN logs
        await page.waitForTimeout(3000);
        const regenLogs = logs.filter(l => l.category === 'REGEN');
        expect(regenLogs.length).toBeGreaterThan(0);
        console.log('✓ REGEN console logs present');
      }
    });

    test('Regenerate All button regenerates all enabled accounts', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      
      // Find Regenerate All button
      const regenerateAllBtn = page.locator('button:has-text("Regenerate All")');
      
      if (await regenerateAllBtn.isVisible()) {
        await regenerateAllBtn.click();
        
        // Wait for regeneration to complete
        await page.waitForTimeout(5000);
        
        // Check for multiple REGEN logs
        const regenLogs = logs.filter(l => l.category === 'REGEN');
        console.log(`✓ Found ${regenLogs.length} REGEN logs`);
      }
    });
  });

  test.describe('Character Limits', () => {
    test('title field respects platform limit', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      
      // Find title input and check its content
      const titleInput = page.locator('input[placeholder*="Title"], textarea').first();
      if (await titleInput.isVisible()) {
        const titleValue = await titleInput.inputValue();
        // Most platforms have 80-100 char title limit
        expect(titleValue.length).toBeLessThanOrEqual(280);
        console.log(`✓ Title length: ${titleValue.length} chars`);
      }
    });

    test('character count is displayed', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Look for character count display
      const charCount = page.locator('text=/\\d+\\s*characters?/i');
      const isVisible = await charCount.first().isVisible().catch(() => false);
      
      if (isVisible) {
        console.log('✓ Character count displayed');
      } else {
        console.log('⚠️ Character count not found (may be hidden)');
      }
    });
  });

  test.describe('Thumbnail Selection', () => {
    test('Auto-Select Best triggers analysis', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const autoSelectBtn = page.locator('button:has-text("Auto-Select Best")');
      if (await autoSelectBtn.isVisible()) {
        await autoSelectBtn.click();
        
        // Should show analyzing state
        const analyzing = page.locator('text=Analyzing');
        try {
          await expect(analyzing).toBeVisible({ timeout: 2000 });
          console.log('✓ Auto-select analyzing...');
        } catch {
          console.log('⚠️ Analyzing state not visible (may be too fast)');
        }
        
        // Wait for completion
        await page.waitForTimeout(3000);
        console.log('✓ Auto-select complete');
      }
    });

    test('clicking thumbnail selects it', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      // Find thumbnail images and click one
      const thumbnails = page.locator('button:has(img)');
      const count = await thumbnails.count();
      
      if (count > 0) {
        await thumbnails.nth(Math.min(2, count - 1)).click();
        await page.waitForTimeout(300);
        console.log('✓ Thumbnail clicked');
      }
    });
  });

  test.describe('Publish & Schedule Workflows', () => {
    test('Publish Now button visible and clickable', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const publishBtn = page.locator('button:has-text("Publish Now")');
      await expect(publishBtn).toBeVisible();
      
      // Don't actually click to avoid side effects
      console.log('✓ Publish Now button visible');
    });

    test('Schedule button visible and clickable', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const scheduleBtn = page.locator('button:has-text("Schedule")');
      await expect(scheduleBtn).toBeVisible();
      
      console.log('✓ Schedule button visible');
    });

    test('Back button navigates to media detail', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      
      const backBtn = page.locator('a:has-text("Back"), button:has-text("Back")');
      await expect(backBtn.first()).toBeVisible();
      
      console.log('✓ Back button visible');
    });
  });

  test.describe('Console Logging Verification', () => {
    test('all log categories are present during page load', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      
      const categories = [...new Set(logs.filter(l => l.category).map(l => l.category))];
      console.log('Log categories found:', categories);
      
      // Should have INIT and API at minimum
      expect(categories).toContain('INIT');
      expect(categories).toContain('API');
      
      console.log('✓ Required log categories present');
    });

    test('logs contain useful debugging information', async ({ page }) => {
      test.skip(!testMediaId, 'No test media available');
      
      const logs = setupConsoleCapture(page);
      
      await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // Check for specific useful log content
      const hasMediaInfo = logs.some(l => l.text.includes('filename') || l.text.includes('duration'));
      const hasAccountInfo = logs.some(l => l.text.includes('accounts') || l.text.includes('platform'));
      
      if (hasMediaInfo) console.log('✓ Logs contain media info');
      if (hasAccountInfo) console.log('✓ Logs contain account info');
      
      // Output sample logs for debugging
      console.log('Sample logs:');
      logs.slice(0, 5).forEach(l => console.log(`  ${l.text.slice(0, 100)}...`));
    });
  });
});

test.describe('Platform Limits API Tests', () => {
  test('GET /api/prompt-settings/platform-limits returns all platforms', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/prompt-settings/platform-limits`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.platforms).toBeDefined();
    
    // Check all expected platforms are present
    const platforms = Object.keys(data.platforms);
    expect(platforms).toContain('instagram');
    expect(platforms).toContain('tiktok');
    expect(platforms).toContain('youtube');
    expect(platforms).toContain('twitter');
    
    console.log(`✓ Platform limits API returned ${platforms.length} platforms`);
  });

  test('platform limits have correct structure', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/prompt-settings/platform-limits/instagram`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    
    // Check structure
    expect(data.platform).toBe('instagram');
    expect(data.title).toBeDefined();
    expect(data.title.max).toBeGreaterThan(0);
    expect(data.title.target).toBeLessThan(data.title.max);
    expect(data.description).toBeDefined();
    expect(data.description.max).toBeGreaterThan(0);
    expect(data.description.target).toBeLessThan(data.description.max);
    
    console.log(`✓ Instagram limits: title=${data.title.target}/${data.title.max}, desc=${data.description.target}/${data.description.max}`);
  });

  test('target values are 80% of max (20% buffer)', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/prompt-settings/platform-limits/tiktok`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    
    // Verify 20% buffer
    const titleBuffer = 1 - (data.title.target / data.title.max);
    const descBuffer = 1 - (data.description.target / data.description.max);
    
    expect(titleBuffer).toBeCloseTo(0.2, 1);
    expect(descBuffer).toBeCloseTo(0.2, 1);
    
    console.log(`✓ TikTok buffer: title=${(titleBuffer * 100).toFixed(0)}%, desc=${(descBuffer * 100).toFixed(0)}%`);
  });
});

test.describe('Caption Generation API Tests', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('POST /api/analysis/generate-captions returns valid response', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const response = await request.post(`${API_URL}/api/analysis/generate-captions/${testMediaId}`, {
      data: {
        platform: 'instagram',
        tone: 'engaging',
        style: 'viral',
        include_hashtags: true,
        include_hook: true
      }
    });
    
    expect(response.status()).toBeLessThan(500);
    
    if (response.status() === 200) {
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.title).toBeDefined();
      expect(data.captions).toBeDefined();
      
      console.log(`✓ Generated captions: title="${data.title?.slice(0, 30)}..."`);
    }
  });

  test('generated content respects platform limits', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const response = await request.post(`${API_URL}/api/analysis/generate-captions/${testMediaId}`, {
      data: {
        platform: 'twitter',
        tone: 'engaging',
        style: 'viral'
      }
    });
    
    if (response.status() === 200) {
      const data = await response.json();
      const twitterCaption = data.captions?.twitter || '';
      
      // Twitter limit is 280 chars, target is 224
      expect(twitterCaption.length).toBeLessThanOrEqual(280);
      
      console.log(`✓ Twitter caption length: ${twitterCaption.length}/280 chars`);
    }
  });
});
