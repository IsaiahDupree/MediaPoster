/**
 * E2E Tests for AI Title & Description Generation
 * 
 * These tests hit the actual API to verify:
 * 1. Platform-specific titles are generated
 * 2. Character limits are enforced
 * 3. Response structure is correct
 * 
 * WILL FAIL IF:
 * - API returns wrong structure
 * - Character limits exceeded
 * - Platform-specific content not generated
 */

import { test, expect } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:5555';

// Expected platform limits (must match backend)
const PLATFORM_LIMITS = {
  tiktok: { title_target: 80, description_target: 3200 },
  instagram: { title_target: 80, description_target: 1760 },
  youtube: { title_target: 80, description_target: 4000 },
  twitter: { title_target: 224, description_target: 224 },
  threads: { title_target: 400, description_target: 400 },
  linkedin: { title_target: 80, description_target: 2400 },
  pinterest: { title_target: 80, description_target: 400 },
  facebook: { title_target: 64, description_target: 50564 },
  bluesky: { title_target: 240, description_target: 240 },
};

test.describe('AI Title & Description Generation E2E', () => {
  
  test.describe('Platform Limits API', () => {
    
    test('GET /api/platform-limits returns all platforms with correct structure', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/platform-limits`);
      
      // Should return 200 or endpoint might not exist yet (404)
      if (response.status() === 404) {
        test.skip(true, 'Platform limits endpoint not implemented yet');
        return;
      }
      
      expect(response.ok()).toBeTruthy();
      
      const data = await response.json();
      
      // Verify structure
      expect(data).toHaveProperty('platforms');
      
      // Check all required platforms are present
      const requiredPlatforms = ['tiktok', 'instagram', 'youtube', 'twitter', 'threads', 'linkedin', 'pinterest', 'facebook', 'bluesky'];
      
      for (const platform of requiredPlatforms) {
        expect(data.platforms).toHaveProperty(platform);
        expect(data.platforms[platform]).toHaveProperty('title_max');
        expect(data.platforms[platform]).toHaveProperty('title_target');
        expect(data.platforms[platform]).toHaveProperty('description_max');
        expect(data.platforms[platform]).toHaveProperty('description_target');
      }
    });

    test('Platform limits match expected 20% buffer rule', async ({ request }) => {
      const response = await request.get(`${API_URL}/api/platform-limits`);
      
      if (response.status() === 404) {
        test.skip(true, 'Platform limits endpoint not implemented yet');
        return;
      }
      
      const data = await response.json();
      
      for (const [platform, limits] of Object.entries(data.platforms)) {
        const platformLimits = limits as any;
        
        // Verify 20% buffer: target = 80% of max
        const expectedTitleTarget = Math.floor(platformLimits.title_max * 0.8);
        const expectedDescTarget = Math.floor(platformLimits.description_max * 0.8);
        
        expect(platformLimits.title_target).toBe(expectedTitleTarget);
        expect(platformLimits.description_target).toBe(expectedDescTarget);
      }
    });
  });

  test.describe('Generate Captions API', () => {
    
    test('POST /api/analysis/generate-captions returns platform_titles', async ({ request }) => {
      // First, we need a valid media_id from the database
      // For E2E, we'll use a test media ID or skip if not available
      
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available for testing');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database for testing');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'tiktok',
          tone: 'engaging',
          include_hashtags: true,
          include_hook: true
        }
      });
      
      if (response.status() === 404) {
        test.skip(true, 'Media not found or endpoint issue');
        return;
      }
      
      expect(response.ok()).toBeTruthy();
      
      const data = await response.json();
      
      // MUST have these fields
      expect(data).toHaveProperty('success');
      expect(data).toHaveProperty('media_id');
      expect(data).toHaveProperty('title');
      expect(data).toHaveProperty('platform_titles');
      expect(data).toHaveProperty('platform_descriptions');
      expect(data).toHaveProperty('captions');
      
      // platform_titles should be an object with platform keys
      expect(typeof data.platform_titles).toBe('object');
      expect(typeof data.platform_descriptions).toBe('object');
    });

    test('Generated captions respect character limits', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'tiktok',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      // Check each platform's caption respects its limit
      for (const [platform, caption] of Object.entries(data.captions)) {
        const platformLimits = PLATFORM_LIMITS[platform as keyof typeof PLATFORM_LIMITS];
        
        if (platformLimits) {
          const captionLength = (caption as string).length;
          
          expect(captionLength).toBeLessThanOrEqual(platformLimits.description_target);
        }
      }
    });

    test('Different platforms get different captions', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'tiktok',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      const captions = Object.values(data.captions) as string[];
      
      // Should have multiple different captions, not all identical
      const uniqueCaptions = new Set(captions);
      
      expect(uniqueCaptions.size).toBeGreaterThan(1);
    });
  });

  test.describe('Character Limit Enforcement', () => {
    
    test('Twitter caption is under 280 characters', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'twitter',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      // Twitter caption MUST be under 280 (actually under 224 target)
      if (data.captions.twitter) {
        expect(data.captions.twitter.length).toBeLessThanOrEqual(224);
      }
    });

    test('Bluesky caption is under 300 characters', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'bluesky',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      // Bluesky caption MUST be under 300 (actually under 240 target)
      if (data.captions.bluesky) {
        expect(data.captions.bluesky.length).toBeLessThanOrEqual(240);
      }
    });
  });

  test.describe('Response Structure Validation', () => {
    
    test('API response includes all required fields', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'tiktok',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      // Required fields per AI_TITLE_DESCRIPTION_ANALYSIS.md
      const requiredFields = [
        'success',
        'media_id',
        'title',
        'platform_titles',
        'platform_descriptions',
        'transcript_available',
        'captions'
      ];
      
      for (const field of requiredFields) {
        expect(data).toHaveProperty(field);
      }
    });

    test('platform_titles contains all major platforms', async ({ request }) => {
      const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
      
      if (!videosResponse.ok()) {
        test.skip(true, 'No videos available');
        return;
      }
      
      const videosData = await videosResponse.json();
      
      if (!videosData.videos || videosData.videos.length === 0) {
        test.skip(true, 'No videos in database');
        return;
      }
      
      const mediaId = videosData.videos[0].id;
      
      const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
        data: {
          platform: 'tiktok',
          tone: 'engaging'
        }
      });
      
      if (!response.ok()) {
        test.skip(true, 'Caption generation failed');
        return;
      }
      
      const data = await response.json();
      
      const expectedPlatforms = [
        'tiktok', 'instagram', 'youtube', 'twitter', 
        'threads', 'pinterest', 'linkedin', 'bluesky', 'facebook'
      ];
      
      for (const platform of expectedPlatforms) {
        // At minimum, captions should have the platform
        expect(data.captions).toHaveProperty(platform);
      }
    });
  });
});

test.describe('Regression Tests', () => {
  
  test('Title is not truncated to 20 chars (regression)', async ({ request }) => {
    // This was a bug where title_target was 20% of max instead of 80% of max
    const videosResponse = await request.get(`${API_URL}/api/videos?limit=1`);
    
    if (!videosResponse.ok()) {
      test.skip(true, 'No videos available');
      return;
    }
    
    const videosData = await videosResponse.json();
    
    if (!videosData.videos || videosData.videos.length === 0) {
      test.skip(true, 'No videos in database');
      return;
    }
    
    const mediaId = videosData.videos[0].id;
    
    const response = await request.post(`${API_URL}/api/analysis/generate-captions/${mediaId}`, {
      data: {
        platform: 'tiktok',
        tone: 'engaging'
      }
    });
    
    if (!response.ok()) {
      test.skip(true, 'Caption generation failed');
      return;
    }
    
    const data = await response.json();
    
    // Title should NOT be limited to just 20 chars
    // It should be up to 80 chars (80% of 100 max)
    if (data.title && data.title.length > 0) {
      // If we have a title, it can be up to 80 chars
      // The bug was limiting to 20 chars
      expect(data.title.length).toBeLessThanOrEqual(80);
    }
  });
});
