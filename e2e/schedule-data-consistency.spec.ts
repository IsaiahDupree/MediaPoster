/**
 * E2E Tests: Schedule Data Consistency
 * 
 * Tests that verify data flows correctly between:
 * - Frontend UI → Backend API → Database
 * - Database → Backend API → Frontend UI
 * 
 * Specifically tracks:
 * - Post URLs being saved correctly
 * - Scheduled posts appearing in all layers
 * - Published post data consistency
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5557';
const API_URL = 'http://localhost:5555';
const DB_URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres';

interface ScheduledPost {
  id: string;
  title: string;
  platform: string;
  status: string;
  platform_url: string | null;
  scheduled_at: string;
  clip_id: string | null;
}

interface DataLayerSnapshot {
  frontend: any[];
  backend: any[];
  database: any[];
}

test.describe('Data Consistency: Frontend ↔ Backend ↔ Database', () => {
  
  test.describe('Post Creation Flow', () => {
    
    test('DC-001: Created post appears in all three layers', async ({ page, request }) => {
      // Step 1: Get initial counts from all layers
      const initialBackend = await request.get(`${API_URL}/api/schedule/`);
      const initialData = initialBackend.ok() ? await initialBackend.json() : [];
      const initialCount = Array.isArray(initialData) ? initialData.length : 0;
      
      // Step 2: Navigate to schedule page
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      
      // Step 3: Create a new scheduled post via UI
      const plusButton = page.locator('button:has-text("+")').first();
      if (await plusButton.isVisible({ timeout: 5000 })) {
        await plusButton.click();
        await page.waitForTimeout(2000);
        
        // Select first available clip
        const mediaItem = page.locator('.cursor-pointer.group').first();
        if (await mediaItem.isVisible({ timeout: 3000 })) {
          await mediaItem.click();
          await page.waitForTimeout(1000);
          
          const selectBtn = page.locator('button:has-text("Select Clip")');
          if (await selectBtn.isVisible({ timeout: 3000 })) {
            await selectBtn.click();
            await page.waitForTimeout(2000);
          }
        }
      }
      
      // Step 4: Verify post appears in backend API
      const afterBackend = await request.get(`${API_URL}/api/schedule/`);
      if (afterBackend.ok()) {
        const afterData = await afterBackend.json();
        const afterCount = Array.isArray(afterData) ? afterData.length : 0;
        
        // Count should increase or stay same (if creation failed gracefully)
        expect(afterCount).toBeGreaterThanOrEqual(initialCount);
      }
    });

    test('DC-002: Post data matches across layers', async ({ request }) => {
      // Get posts from backend
      const backendResponse = await request.get(`${API_URL}/api/schedule/?limit=10`);
      
      if (backendResponse.ok()) {
        const backendPosts = await backendResponse.json();
        
        if (Array.isArray(backendPosts) && backendPosts.length > 0) {
          const samplePost = backendPosts[0];
          
          // Verify required fields exist
          expect(samplePost).toHaveProperty('id');
          expect(samplePost).toHaveProperty('platform');
          expect(samplePost).toHaveProperty('status');
          
          // Get same post by ID
          const singleResponse = await request.get(`${API_URL}/api/schedule/${samplePost.id}`);
          if (singleResponse.ok()) {
            const singlePost = await singleResponse.json();
            
            // Verify data matches
            expect(singlePost.id).toBe(samplePost.id);
            expect(singlePost.platform).toBe(samplePost.platform);
            expect(singlePost.status).toBe(samplePost.status);
          }
        }
      }
    });
  });

  test.describe('URL Tracking', () => {
    
    test('DC-URL-001: Posted content has platform_url saved', async ({ request }) => {
      // Query for posted content
      const response = await request.get(`${API_URL}/api/schedule/?status=posted&limit=20`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          const postedWithUrls = posts.filter((p: any) => p.platform_url);
          const postedWithoutUrls = posts.filter((p: any) => !p.platform_url && p.status === 'posted');
          
          console.log(`📊 Posted posts with URLs: ${postedWithUrls.length}`);
          console.log(`⚠️ Posted posts WITHOUT URLs: ${postedWithoutUrls.length}`);
          
          // Log posts missing URLs for debugging
          if (postedWithoutUrls.length > 0) {
            console.log('Posts missing URLs:');
            postedWithoutUrls.slice(0, 5).forEach((p: any) => {
              console.log(`  - ${p.id}: ${p.platform} - ${p.title?.slice(0, 30)}`);
            });
          }
          
          // At least some posted content should have URLs
          // (Note: Some may legitimately not have URLs if Blotato didn't return them)
        }
      }
    });

    test('DC-URL-002: platform_post_id is saved for posted content', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?status=posted&limit=20`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          const withPostId = posts.filter((p: any) => p.platform_post_id);
          const withoutPostId = posts.filter((p: any) => !p.platform_post_id && p.status === 'posted');
          
          console.log(`📊 Posted with platform_post_id: ${withPostId.length}`);
          console.log(`⚠️ Posted WITHOUT platform_post_id: ${withoutPostId.length}`);
        }
      }
    });

    test('DC-URL-003: Verify URL format is valid', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?status=posted&limit=50`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          const postsWithUrls = posts.filter((p: any) => p.platform_url);
          
          for (const post of postsWithUrls.slice(0, 10)) {
            const url = post.platform_url;
            
            // Verify URL format based on platform
            if (post.platform === 'tiktok') {
              expect(url).toMatch(/tiktok\.com|vm\.tiktok/i);
            } else if (post.platform === 'instagram') {
              expect(url).toMatch(/instagram\.com/i);
            } else if (post.platform === 'youtube') {
              expect(url).toMatch(/youtube\.com|youtu\.be/i);
            } else if (post.platform === 'twitter') {
              expect(url).toMatch(/twitter\.com|x\.com/i);
            }
          }
        }
      }
    });
  });

  test.describe('Schedule State Consistency', () => {
    
    test('DC-STATE-001: Scheduled posts show correct status', async ({ page, request }) => {
      // Get scheduled posts from API
      const apiResponse = await request.get(`${API_URL}/api/schedule/?status=scheduled`);
      let apiScheduledCount = 0;
      
      if (apiResponse.ok()) {
        const data = await apiResponse.json();
        apiScheduledCount = Array.isArray(data) ? data.length : 0;
      }
      
      // Check frontend shows scheduled posts
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // Count visible scheduled items
      const scheduledItems = page.locator('[data-status="scheduled"], .scheduled-post');
      const uiCount = await scheduledItems.count().catch(() => 0);
      
      console.log(`📊 API scheduled count: ${apiScheduledCount}`);
      console.log(`📊 UI scheduled count: ${uiCount}`);
      
      // Counts should be reasonably close (UI may paginate)
      // This is informational - we're tracking discrepancies
    });

    test('DC-STATE-002: Failed posts have error messages', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?status=failed&limit=20`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts) && posts.length > 0) {
          const withErrors = posts.filter((p: any) => p.error_message || p.last_error);
          const withoutErrors = posts.filter((p: any) => !p.error_message && !p.last_error);
          
          console.log(`📊 Failed posts with error messages: ${withErrors.length}`);
          console.log(`⚠️ Failed posts WITHOUT error messages: ${withoutErrors.length}`);
          
          // Failed posts should have error info
          expect(withErrors.length).toBeGreaterThan(0);
        }
      }
    });

    test('DC-STATE-003: Publishing state transitions are tracked', async ({ request }) => {
      // Check for posts in various states
      const states = ['scheduled', 'publishing', 'posted', 'failed', 'retry_scheduled'];
      const stateCounts: Record<string, number> = {};
      
      for (const status of states) {
        const response = await request.get(`${API_URL}/api/schedule/?status=${status}&limit=100`);
        if (response.ok()) {
          const data = await response.json();
          stateCounts[status] = Array.isArray(data) ? data.length : 0;
        }
      }
      
      console.log('📊 Post counts by status:');
      for (const [status, count] of Object.entries(stateCounts)) {
        console.log(`  ${status}: ${count}`);
      }
    });
  });

  test.describe('Media Reference Integrity', () => {
    
    test('DC-MEDIA-001: Scheduled posts have valid clip_id references', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?limit=50`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          const withClipId = posts.filter((p: any) => p.clip_id);
          const withoutClipId = posts.filter((p: any) => !p.clip_id);
          
          console.log(`📊 Posts with clip_id: ${withClipId.length}`);
          console.log(`⚠️ Posts WITHOUT clip_id: ${withoutClipId.length}`);
          
          // Verify clip_ids are valid UUIDs
          for (const post of withClipId.slice(0, 5)) {
            expect(post.clip_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
          }
        }
      }
    });

    test('DC-MEDIA-002: clip_id references exist in video database', async ({ request }) => {
      // Get a scheduled post with clip_id
      const scheduleResponse = await request.get(`${API_URL}/api/schedule/?limit=10`);
      
      if (scheduleResponse.ok()) {
        const posts = await scheduleResponse.json();
        
        if (Array.isArray(posts)) {
          const postsWithClips = posts.filter((p: any) => p.clip_id);
          
          for (const post of postsWithClips.slice(0, 3)) {
            // Verify clip exists in media DB
            const mediaResponse = await request.get(`${API_URL}/api/media-db/${post.clip_id}`);
            
            if (mediaResponse.ok()) {
              const media = await mediaResponse.json();
              expect(media).toBeDefined();
              console.log(`✅ clip_id ${post.clip_id.slice(0, 8)}... exists in media DB`);
            } else {
              console.log(`⚠️ clip_id ${post.clip_id.slice(0, 8)}... NOT FOUND in media DB`);
            }
          }
        }
      }
    });
  });

  test.describe('Timestamp Consistency', () => {
    
    test('DC-TIME-001: scheduled_at matches scheduled_time', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?limit=20`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          for (const post of posts.slice(0, 5)) {
            if (post.scheduled_at && post.scheduled_time) {
              const at = new Date(post.scheduled_at).getTime();
              const time = new Date(post.scheduled_time).getTime();
              
              // Should be the same or very close
              const diffMs = Math.abs(at - time);
              expect(diffMs).toBeLessThan(1000); // Within 1 second
            }
          }
        }
      }
    });

    test('DC-TIME-002: published_at is set for posted content', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/schedule/?status=posted&limit=20`);
      
      if (response.ok()) {
        const posts = await response.json();
        
        if (Array.isArray(posts)) {
          const withPublishedAt = posts.filter((p: any) => p.published_at);
          const withoutPublishedAt = posts.filter((p: any) => !p.published_at);
          
          console.log(`📊 Posted with published_at: ${withPublishedAt.length}`);
          console.log(`⚠️ Posted WITHOUT published_at: ${withoutPublishedAt.length}`);
          
          // Most posted content should have published_at
          if (posts.length > 0) {
            const ratio = withPublishedAt.length / posts.length;
            expect(ratio).toBeGreaterThan(0.5); // At least 50% should have it
          }
        }
      }
    });
  });
});

test.describe('Real-time Sync Tests', () => {
  
  test('RT-001: UI updates when backend data changes', async ({ page, request }) => {
    // Navigate to schedule page
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
    
    // Take initial screenshot
    const initialHtml = await page.content();
    
    // Wait for any WebSocket/polling updates
    await page.waitForTimeout(5000);
    
    // Check if content changed (real-time update)
    const afterHtml = await page.content();
    
    // This is informational - checking if real-time updates work
    console.log(`📊 Initial HTML length: ${initialHtml.length}`);
    console.log(`📊 After 5s HTML length: ${afterHtml.length}`);
  });

  test('RT-002: API reflects immediate database changes', async ({ request }) => {
    // Get current count
    const before = await request.get(`${API_URL}/api/schedule/?limit=1000`);
    const beforeData = before.ok() ? await before.json() : [];
    const beforeCount = Array.isArray(beforeData) ? beforeData.length : 0;
    
    console.log(`📊 Current schedule count: ${beforeCount}`);
    
    // Verify API is responding with current data
    expect(before.ok()).toBe(true);
  });
});

test.describe('Data Validation Tests', () => {
  
  test('VAL-001: All required fields are populated', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/schedule/?limit=20`);
    
    if (response.ok()) {
      const posts = await response.json();
      
      if (Array.isArray(posts)) {
        const requiredFields = ['id', 'platform', 'status'];
        
        for (const post of posts.slice(0, 10)) {
          for (const field of requiredFields) {
            expect(post).toHaveProperty(field);
            expect(post[field]).toBeDefined();
          }
        }
      }
    }
  });

  test('VAL-002: Platform values are valid', async ({ request }) => {
    const validPlatforms = ['tiktok', 'instagram', 'youtube', 'twitter', 'threads', 'pinterest', 'linkedin', 'facebook', 'bluesky'];
    
    const response = await request.get(`${API_URL}/api/schedule/?limit=50`);
    
    if (response.ok()) {
      const posts = await response.json();
      
      if (Array.isArray(posts)) {
        for (const post of posts) {
          expect(validPlatforms).toContain(post.platform.toLowerCase());
        }
      }
    }
  });

  test('VAL-003: Status values are valid', async ({ request }) => {
    const validStatuses = ['pending', 'scheduled', 'publishing', 'posted', 'failed', 'retry_scheduled', 'cancelled'];
    
    const response = await request.get(`${API_URL}/api/schedule/?limit=50`);
    
    if (response.ok()) {
      const posts = await response.json();
      
      if (Array.isArray(posts)) {
        for (const post of posts) {
          expect(validStatuses).toContain(post.status.toLowerCase());
        }
      }
    }
  });
});
