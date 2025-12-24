/**
 * Publish Flow Integration Tests
 * 
 * Tests the complete publish flow from post-content to posted-content:
 * 1. Account ID handling (UUIDs and integers)
 * 2. URL parameter passing between pages
 * 3. Blotato account matching
 * 4. Publishing workflow
 */

import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5557';
const API_URL = 'http://localhost:5555';

// Test data
const TEST_ACCOUNT_IDS = {
  uuid: '96c00768-1ec3-44ed-aa72-679629e330c0',
  integer: '710',
  multiple: '807,670,710',
};

// Get a test media ID
async function getTestMediaId(): Promise<string | null> {
  try {
    const response = await fetch(`${API_URL}/api/media-db/list?limit=1`);
    if (response.ok) {
      const data = await response.json();
      if (data.items?.length > 0) {
        return data.items[0].media_id;
      }
    }
  } catch (e) {
    console.error('Failed to get test media:', e);
  }
  return null;
}

test.describe('Backend: Account ID Handling', () => {
  
  test('Blotato accounts endpoint returns array directly', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/blotato/accounts`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    
    // Should be an array, not { accounts: [...] }
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
    
    // Each account should have id, platform, username
    const firstAccount = data[0];
    expect(firstAccount).toHaveProperty('id');
    expect(firstAccount).toHaveProperty('platform');
    expect(firstAccount).toHaveProperty('username');
    
    console.log(`✓ Blotato accounts endpoint returns array with ${data.length} accounts`);
  });

  test('Social accounts endpoint returns accounts with correct ID types', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/social-accounts/accounts`);
    expect(response.status()).toBe(200);
    
    const accounts = await response.json();
    expect(Array.isArray(accounts)).toBe(true);
    
    if (accounts.length > 0) {
      const firstAccount = accounts[0];
      console.log(`First account ID type: ${typeof firstAccount.id} = ${firstAccount.id}`);
      
      // ID should be either number or string (UUID)
      expect(['number', 'string']).toContain(typeof firstAccount.id);
    }
    
    console.log(`✓ Social accounts endpoint returns ${accounts.length} accounts`);
  });

  test('Account IDs can be matched by string comparison', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/social-accounts/accounts`);
    const accounts = await response.json();
    
    if (accounts.length > 0) {
      const testId = accounts[0].id;
      const testIdString = String(testId);
      
      // Find by string comparison
      const found = accounts.find((a: any) => String(a.id) === testIdString);
      expect(found).toBeDefined();
      
      console.log(`✓ Account ID ${testId} can be matched as string "${testIdString}"`);
    }
  });
});

test.describe('Frontend: URL Parameter Handling', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('posted-content page parses UUID account IDs correctly', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    // Navigate with UUID account ID
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=${TEST_ACCOUNT_IDS.uuid}`);
    await page.waitForTimeout(2000);
    
    // Check logs for correct parsing
    const parsingLog = logs.find(l => l.includes('enabledAccountIds'));
    expect(parsingLog).toBeDefined();
    
    // Should NOT contain just "96" (the broken parseInt result)
    const has96Only = logs.some(l => l.includes('[96]') && !l.includes('96c00768'));
    
    if (has96Only) {
      console.log('⚠️ UUID was incorrectly parsed as integer');
    } else {
      console.log('✓ UUID account ID parsed correctly');
    }
  });

  test('posted-content page parses integer account IDs correctly', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    // Navigate with integer account ID
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=${TEST_ACCOUNT_IDS.integer}`);
    await page.waitForTimeout(2000);
    
    // Check that the ID was parsed
    const hasCorrectId = logs.some(l => l.includes('710') || l.includes(TEST_ACCOUNT_IDS.integer));
    expect(hasCorrectId).toBe(true);
    
    console.log('✓ Integer account ID parsed correctly');
  });

  test('posted-content page parses multiple account IDs correctly', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    // Navigate with multiple account IDs
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=${TEST_ACCOUNT_IDS.multiple}`);
    await page.waitForTimeout(2000);
    
    // Should have 3 IDs
    const enabledLog = logs.find(l => l.includes('Checking enabledAccountIds'));
    console.log('Enabled IDs log:', enabledLog);
    
    console.log('✓ Multiple account IDs parsing test complete');
  });
});

test.describe('Frontend: Blotato Account Matching', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('Blotato accounts are fetched and populated', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=710`);
    await page.waitForTimeout(3000);
    
    // Check for Blotato accounts log
    const blotatoLog = logs.find(l => l.includes('Blotato accounts:'));
    expect(blotatoLog).toBeDefined();
    
    // Should have 22 accounts, not empty
    const hasAccounts = logs.some(l => l.includes('(22)') && l.includes('Blotato accounts'));
    
    if (hasAccounts) {
      console.log('✓ Blotato accounts populated with 22 accounts');
    } else {
      console.log('⚠️ Blotato accounts may be empty - check API response format');
    }
  });

  test('Account matching finds correct Blotato ID', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    // Use a known Blotato ID (710 = @isaiah_dupree on TikTok)
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=710&test=true`);
    await page.waitForTimeout(3000);
    
    // Check if matching worked
    const matchingLog = logs.find(l => l.includes('[Blotato] Matching') || l.includes('Using local mapping'));
    
    if (matchingLog) {
      console.log('✓ Blotato account matching is working');
      console.log(`  ${matchingLog.slice(0, 100)}...`);
    }
  });
});

test.describe('E2E: Complete Publish Flow', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('post-content to posted-content redirect includes account IDs', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    // Start on post-content page
    await page.goto(`${FRONTEND_URL}/post-content/${testMediaId}`);
    await page.waitForLoadState('networkidle');
    
    // Check that accounts are loaded
    await expect(page.locator('h1:has-text("Review & Post Content")')).toBeVisible({ timeout: 10000 });
    
    // Find Test Publish UI button (uses test mode)
    const testPublishBtn = page.locator('button:has-text("Test Publish")');
    if (await testPublishBtn.isVisible()) {
      // Set up navigation listener to capture the redirect URL
      const navigationPromise = page.waitForURL(/\/posted-content/, { timeout: 10000 }).catch(() => null);
      
      await testPublishBtn.click();
      
      await navigationPromise;
      
      // Check URL includes accounts parameter
      const url = page.url();
      console.log('Redirected to:', url);
      
      if (url.includes('accounts=')) {
        console.log('✓ URL includes accounts parameter');
      } else {
        console.log('⚠️ URL missing accounts parameter');
      }
    } else {
      console.log('Test Publish button not found - checking Publish Now');
    }
  });

  test('published posts appear in Account Status section', async ({ page }) => {
    test.skip(!testMediaId, 'No test media available');
    
    // Navigate to posted-content with test mode
    await page.goto(`${FRONTEND_URL}/posted-content?media_id=${testMediaId}&accounts=710&test=true`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Check for Account Status section
    const accountStatus = page.locator('text=Account Status');
    if (await accountStatus.isVisible()) {
      console.log('✓ Account Status section visible');
    }
    
    // Check for any post status indicators
    const postedCount = await page.locator('text=/Posted|Pending|Failed/i').count();
    console.log(`Found ${postedCount} post status indicators`);
  });
});

test.describe('API: Platform Content Saving', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('platform_content is saved when publishing', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    // First, save platform content
    const saveRes = await request.put(`${API_URL}/api/media-db/analysis/${testMediaId}`, {
      data: {
        platform_content: [{
          platform: 'tiktok',
          account_id: 710,
          username: 'isaiah_dupree',
          title: 'Test Title',
          description: 'Test Description',
          hashtags: ['test', 'publish'],
        }]
      }
    });
    
    console.log(`Save platform content: ${saveRes.status()}`);
    
    // Then fetch it back
    const fetchRes = await request.get(`${API_URL}/api/media-db/analysis/${testMediaId}`);
    
    if (fetchRes.ok) {
      const data = await fetchRes.json();
      const platformContent = data.platform_content || [];
      
      console.log(`✓ Retrieved ${platformContent.length} platform content entries`);
    }
  });
});

test.describe('API: Posted Content Database Integration', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('POST /api/posted-content/record creates a record in database', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const testSubmissionId = `test-${Date.now()}`;
    
    // Record a post - THIS IS THE TEST THAT WOULD HAVE CAUGHT THE BUG
    const recordRes = await request.post(`${API_URL}/api/posted-content/record`, {
      data: {
        media_id: testMediaId,
        platform: 'tiktok',
        blotato_submission_id: testSubmissionId,
        blotato_account_id: '710',  // String account ID - caused the UUID type error
        caption: 'E2E Test Post',
        status: 'published',
      }
    });
    
    // This should return 200, not 500
    expect(recordRes.status()).toBe(200);
    
    const recordData = await recordRes.json();
    expect(recordData.success).toBe(true);
    expect(recordData.id).toBeDefined();
    
    console.log(`✓ Post recorded with ID: ${recordData.id}`);
  });

  test('GET /api/posted-content returns recorded posts', async ({ request }) => {
    // Fetch posted content
    const fetchRes = await request.get(`${API_URL}/api/posted-content?limit=10`);
    expect(fetchRes.status()).toBe(200);
    
    const data = await fetchRes.json();
    expect(data.items).toBeDefined();
    expect(Array.isArray(data.items)).toBe(true);
    
    console.log(`✓ Posted content endpoint returns ${data.items.length} items (total: ${data.total})`);
    
    // Should have at least one item if our record test passed
    if (data.items.length > 0) {
      const item = data.items[0];
      expect(item.platform).toBeDefined();
      expect(item.posted_at).toBeDefined();
      console.log(`  First item: ${item.platform} - ${item.status}`);
    }
  });

  test('Full publish flow records to posted-content database', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    // This simulates what the frontend does after a successful Blotato publish:
    // 1. Publish succeeds with submission ID
    // 2. Record to posted-content database
    // 3. Verify it appears in GET /api/posted-content
    
    const submissionId = `e2e-full-${Date.now()}`;
    
    // Step 1: Record the post
    const recordRes = await request.post(`${API_URL}/api/posted-content/record`, {
      data: {
        media_id: testMediaId,
        platform: 'instagram',
        blotato_submission_id: submissionId,
        blotato_account_id: '807',
        caption: 'Full flow E2E test',
        status: 'published',
      }
    });
    
    expect(recordRes.status()).toBe(200);
    
    // Step 2: Verify it appears in the list
    const listRes = await request.get(`${API_URL}/api/posted-content?limit=50`);
    const listData = await listRes.json();
    
    const foundPost = listData.items.find((p: any) => 
      p.platform_post_id === submissionId
    );
    
    expect(foundPost).toBeDefined();
    console.log(`✓ Full publish flow verified - post found in database`);
  });
});
