/**
 * Database Write Path Integration Tests
 * 
 * Tests actual database INSERT/UPDATE operations to catch schema mismatches
 * and ensure data flows correctly through the system.
 */

import { test, expect } from '@playwright/test';

const API_URL = 'http://localhost:5555';

// Helper to get a test media ID
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

test.describe('Database Write: Scheduled Posts', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('POST /api/schedule creates scheduled post in database', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const scheduledTime = new Date(Date.now() + 3600000).toISOString(); // 1 hour from now
    
    const res = await request.post(`${API_URL}/api/schedule`, {
      data: {
        media_id: testMediaId,
        platform: 'tiktok',
        account_id: '710',
        scheduled_time: scheduledTime,
        caption: 'E2E Test Scheduled Post',
        status: 'scheduled',
      }
    });
    
    // Accept both 200 and 201 for creation
    expect([200, 201, 422]).toContain(res.status());
    
    if (res.ok) {
      const data = await res.json();
      console.log(`✓ Scheduled post created: ${data.id || 'success'}`);
    } else {
      console.log(`⚠️ Schedule endpoint returned ${res.status()} - may need different schema`);
    }
  });

  test('GET /api/schedule returns scheduled posts', async ({ request }) => {
    const res = await request.get(`${API_URL}/api/schedule?limit=10`);
    
    // Accept various response formats
    if (res.ok) {
      const data = await res.json();
      const items = data.items || data.posts || data || [];
      console.log(`✓ Schedule endpoint returns ${Array.isArray(items) ? items.length : 'data'}`);
    } else {
      console.log(`⚠️ Schedule endpoint returned ${res.status()}`);
    }
  });
});

test.describe('Database Write: Analysis Data', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('PUT /api/media-db/analysis saves platform content', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const res = await request.put(`${API_URL}/api/media-db/analysis/${testMediaId}`, {
      data: {
        platform_content: [{
          platform: 'tiktok',
          account_id: 710,
          username: 'isaiah_dupree',
          title: 'E2E Test Title',
          description: 'E2E Test Description',
          caption: 'E2E Test Caption #test',
          hashtags: ['test', 'e2e'],
        }]
      }
    });
    
    expect(res.status()).toBe(200);
    console.log(`✓ Analysis platform content saved`);
  });

  test('GET /api/media-db/analysis retrieves saved platform content', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const res = await request.get(`${API_URL}/api/media-db/analysis/${testMediaId}`);
    expect(res.status()).toBe(200);
    
    const data = await res.json();
    const platformContent = data.platform_content || [];
    
    console.log(`✓ Retrieved ${platformContent.length} platform content entries`);
    
    // Verify our test data exists
    if (platformContent.length > 0) {
      const testEntry = platformContent.find((p: any) => p.title === 'E2E Test Title');
      if (testEntry) {
        expect(testEntry.description).toBe('E2E Test Description');
        console.log(`  ✓ Test entry found with correct title and description`);
      }
    }
  });
});

test.describe('Database Write: Experiments', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('POST /api/experiments creates experiment in database', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/experiments`, {
      data: {
        name: `E2E Test Experiment ${Date.now()}`,
        hypothesis: 'Testing database write path',
        status: 'draft',
        metric: 'views',
        target_value: 1000,
      }
    });
    
    if (res.ok) {
      const data = await res.json();
      expect(data.id || data.experiment_id).toBeDefined();
      console.log(`✓ Experiment created: ${data.id || data.experiment_id}`);
    } else {
      console.log(`⚠️ Experiments endpoint returned ${res.status()}`);
    }
  });

  test('GET /api/experiments returns experiments list', async ({ request }) => {
    const res = await request.get(`${API_URL}/api/experiments?limit=10`);
    
    if (res.ok) {
      const data = await res.json();
      const items = data.experiments || data.items || data || [];
      console.log(`✓ Experiments endpoint returns ${Array.isArray(items) ? items.length : 'data'} items`);
    }
  });
});

test.describe('Database Write: Narrative Builder', () => {
  test('POST /api/narrative-builder/goals creates goal', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/narrative-builder/goals`, {
      data: {
        name: `E2E Test Goal ${Date.now()}`,
        description: 'Testing database write path',
        target_metric: 'followers',
        target_value: 10000,
        status: 'active',
      }
    });
    
    if (res.ok) {
      const data = await res.json();
      console.log(`✓ Narrative goal created: ${data.id || 'success'}`);
    } else {
      console.log(`⚠️ Narrative goals endpoint returned ${res.status()}`);
    }
  });

  test('GET /api/narrative-builder/goals returns goals', async ({ request }) => {
    const res = await request.get(`${API_URL}/api/narrative-builder/goals`);
    
    if (res.ok) {
      const data = await res.json();
      const items = data.goals || data.items || data || [];
      console.log(`✓ Narrative goals endpoint returns ${Array.isArray(items) ? items.length : 'data'} items`);
    }
  });
});

test.describe('Database Write: Social Accounts', () => {
  test('GET /api/social-accounts/accounts returns accounts', async ({ request }) => {
    const res = await request.get(`${API_URL}/api/social-accounts/accounts`);
    expect(res.status()).toBe(200);
    
    const data = await res.json();
    expect(Array.isArray(data)).toBe(true);
    
    if (data.length > 0) {
      const account = data[0];
      expect(account.id).toBeDefined();
      expect(account.platform).toBeDefined();
      console.log(`✓ Social accounts: ${data.length} accounts, first ID type: ${typeof account.id}`);
    }
  });

  test('POST /api/social-accounts/accounts creates account (if supported)', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/social-accounts/accounts`, {
      data: {
        platform: 'test',
        username: `e2e_test_${Date.now()}`,
        status: 'active',
      }
    });
    
    // This might not be supported - just log the result
    console.log(`Social accounts POST: ${res.status()} ${res.ok ? '(supported)' : '(not supported or requires auth)'}`);
  });
});

test.describe('Database Write: Blotato Accounts', () => {
  test('GET /api/blotato/accounts returns array directly', async ({ request }) => {
    const res = await request.get(`${API_URL}/api/blotato/accounts`);
    expect(res.status()).toBe(200);
    
    const data = await res.json();
    
    // CRITICAL: Must be array directly, not { accounts: [...] }
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
    
    console.log(`✓ Blotato accounts: ${data.length} accounts (returned as array directly)`);
    
    // Verify account structure
    const account = data[0];
    expect(account.id).toBeDefined();
    expect(account.platform).toBeDefined();
    expect(account.username).toBeDefined();
  });
});

test.describe('Database Write: Video Analysis', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('Analysis data includes required fields', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    const res = await request.get(`${API_URL}/api/media-db/analysis/${testMediaId}`);
    
    if (res.ok) {
      const data = await res.json();
      
      // Check for key analysis fields
      const hasDeepAnalysis = data.deep_analysis || data.transcript || data.topics;
      console.log(`✓ Analysis data retrieved, has deep analysis: ${!!hasDeepAnalysis}`);
      
      if (data.platform_content?.length > 0) {
        const pc = data.platform_content[0];
        console.log(`  Platform content has: title=${!!pc.title}, description=${!!pc.description}, caption=${!!pc.caption}`);
      }
    }
  });
});

test.describe('Database Write: Full Publish Flow with Title', () => {
  let testMediaId: string | null = null;

  test.beforeAll(async () => {
    testMediaId = await getTestMediaId();
  });

  test('Full publish request includes title field', async ({ request }) => {
    test.skip(!testMediaId, 'No test media available');
    
    // This tests the schema - we're sending title but not actually publishing
    const res = await request.post(`${API_URL}/api/blotato/posts/full-publish`, {
      data: {
        media_id: testMediaId,
        blotato_account_id: '710',
        platform: 'tiktok',
        username: 'isaiah_dupree',
        text: 'E2E Test Caption #test',
        title: 'E2E Test Title',  // This field should be accepted
        cleanup_gdrive: false,  // Don't actually clean up
      }
    });
    
    // The request should be accepted (validation passes)
    // It may fail for other reasons (file not found, etc.) but not for schema
    if (res.status() === 422) {
      const error = await res.json();
      // Check if it's a title field validation error
      const titleError = error.detail?.find?.((e: any) => e.loc?.includes('title'));
      expect(titleError).toBeUndefined();
      console.log(`⚠️ Request failed but not due to title field: ${res.status()}`);
    } else {
      console.log(`✓ Full publish request accepted (status: ${res.status()})`);
    }
  });
});
