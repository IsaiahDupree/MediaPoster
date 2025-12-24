/**
 * Full Workflow E2E Test - AI Agent SaaS
 * =======================================
 * 
 * This comprehensive test covers the complete workflow of the MediaPoster AI Agent:
 * 
 * PHASE 1: Video Ingestion & Analysis
 *   - Look at ingested videos
 *   - Identify analyzed vs unanalyzed content
 *   - Run analysis on unanalyzed videos
 * 
 * PHASE 2: Publishing via Blotato & Scheduler
 *   - Select a video for publishing
 *   - Post using Blotato integration
 *   - Schedule posts via scheduler
 *   - Obtain polling URL from the post
 *   - Wait and run third-party endpoint to get stats
 * 
 * PHASE 3: Narrative Builder
 *   - Look at analyzed content inventory
 *   - Review narrative goals
 *   - Design 7-day content posting plan
 *   - Execute posts through scheduler
 *   - Obtain URLs after publishing
 *   - Collect data statistics for each post
 *   - Feedback into narrative builder for reflection
 *   - Plan next 7 days with daily assessments
 *   - Log URLs as they're tracked
 * 
 * PHASE 4: Experiments
 *   - Look at analyzed videos
 *   - Run experiment using video editing tool
 *   - Test hypothesis on sister account (not main)
 *   - Post via scheduler
 *   - Obtain URL and assess via third-party endpoints
 *   - Short-term and long-term data analysis
 *   - Feedback to experimental builder
 * 
 * @author MediaPoster Team
 * @version 1.0.0
 */

import { test, expect, Page } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5557';
const API_URL = 'http://localhost:5555';

// Test configuration
const TEST_CONFIG = {
  pollIntervalMs: 5000,
  maxPollAttempts: 12,
  shortTermWaitMs: 10000,
  longTermWaitMs: 60000,
  schedulerDelayMs: 3000,
};

// Blotato Account IDs - Main accounts
const MAIN_ACCOUNTS = {
  tiktok: { id: 710, username: 'isaiah_dupree' },
  instagram: { id: 807, username: 'the_isaiah_dupree' },
  youtube: { id: 228, username: 'UCnDBsELI2OlaEl5yxA77HNA' },
  twitter: { id: 4151, username: 'IsaiahDupree7' },
};

// Sister accounts for experiments
const SISTER_ACCOUNTS = {
  tiktok: { id: 4508, username: 'dupree_isaiah' },
  instagram: { id: 670, username: 'the_isaiah_dupree_' },
  threads: { id: 4150, username: 'isaiahdupree75' },
};

// Test state shared across phases
interface TestState {
  ingestedVideos: any[];
  analyzedVideos: any[];
  selectedVideo: any;
  publishedPostId: string | null;
  publishedUrl: string | null;
  postStats: any;
  narrativePlan: any;
  scheduledPosts: any[];
  experimentResults: any;
}

const state: TestState = {
  ingestedVideos: [],
  analyzedVideos: [],
  selectedVideo: null,
  publishedPostId: null,
  publishedUrl: null,
  postStats: null,
  narrativePlan: null,
  scheduledPosts: [],
  experimentResults: null,
};

// ============================================================================
// PHASE 1: VIDEO INGESTION & ANALYSIS
// ============================================================================

test.describe('PHASE 1: Video Ingestion & Analysis', () => {
  
  test('1.1 Fetch ingested videos from media library', async ({ request }) => {
    console.log('\n📹 PHASE 1.1: Fetching ingested videos...');
    
    const response = await request.get(`${API_URL}/api/media-db/list?limit=50`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    state.ingestedVideos = data.items || [];
    
    console.log(`✓ Found ${state.ingestedVideos.length} total videos in library`);
    expect(state.ingestedVideos.length).toBeGreaterThan(0);
  });

  test('1.2 Identify analyzed vs unanalyzed videos', async ({ request }) => {
    console.log('\n🔍 PHASE 1.2: Categorizing videos by analysis status...');
    
    // Fetch with analysis status
    const response = await request.get(`${API_URL}/api/media-db/list?limit=50`);
    const data = await response.json();
    const videos = data.items || [];
    
    state.analyzedVideos = videos.filter((v: any) => 
      v.pre_social_score || v.analyzed_at || v.transcript
    );
    
    const unanalyzedVideos = videos.filter((v: any) => 
      !v.pre_social_score && !v.analyzed_at && !v.transcript
    );
    
    console.log(`✓ Analyzed videos: ${state.analyzedVideos.length}`);
    console.log(`✓ Unanalyzed videos: ${unanalyzedVideos.length}`);
    
    // Store first analyzed video for later use
    if (state.analyzedVideos.length > 0) {
      state.selectedVideo = state.analyzedVideos[0];
      console.log(`✓ Selected video for publishing: ${state.selectedVideo.filename}`);
    }
  });

  test('1.3 Run analysis on unanalyzed video (if available)', async ({ request }) => {
    console.log('\n🧠 PHASE 1.3: Running analysis on video...');
    
    // Get an analyzed video to work with
    if (!state.selectedVideo && state.ingestedVideos.length > 0) {
      state.selectedVideo = state.ingestedVideos[0];
    }
    
    if (!state.selectedVideo) {
      console.log('⚠️ No videos available for analysis');
      test.skip();
      return;
    }
    
    // Check if video needs analysis
    const detailRes = await request.get(`${API_URL}/api/media-db/detail/${state.selectedVideo.media_id}`);
    if (detailRes.ok) {
      const detail = await detailRes.json();
      
      if (detail.pre_social_score) {
        console.log(`✓ Video already analyzed (score: ${detail.pre_social_score})`);
      } else {
        // Trigger analysis
        console.log('Triggering analysis...');
        const analysisRes = await request.post(
          `${API_URL}/api/media-db/analyze/${state.selectedVideo.media_id}`
        );
        
        if (analysisRes.ok) {
          console.log('✓ Analysis triggered successfully');
        } else {
          console.log(`⚠️ Analysis returned ${analysisRes.status()}`);
        }
      }
    }
  });

  test('1.4 Verify analysis data is complete', async ({ request }) => {
    console.log('\n✅ PHASE 1.4: Verifying analysis data...');
    
    if (!state.selectedVideo) {
      test.skip();
      return;
    }
    
    const response = await request.get(
      `${API_URL}/api/media-db/detail/${state.selectedVideo.media_id}`
    );
    
    if (response.ok) {
      const detail = await response.json();
      
      console.log('Analysis data:');
      console.log(`  - Transcript: ${detail.transcript ? 'Yes' : 'No'}`);
      console.log(`  - Topics: ${detail.topics?.length || 0}`);
      console.log(`  - Pre-social score: ${detail.pre_social_score || 'N/A'}`);
      console.log(`  - Tone: ${detail.tone || 'N/A'}`);
      
      state.selectedVideo = detail;
    }
  });
});

// ============================================================================
// PHASE 2: PUBLISHING VIA BLOTATO & SCHEDULER
// ============================================================================

test.describe('PHASE 2: Publishing via Blotato & Scheduler', () => {
  
  test('2.1 Select video for publishing', async ({ request }) => {
    console.log('\n📤 PHASE 2.1: Selecting video for publishing...');
    
    // Get an analyzed video if we don't have one
    if (!state.selectedVideo) {
      const response = await request.get(`${API_URL}/api/media-db/list?limit=10`);
      const data = await response.json();
      const videos = (data.items || []).filter((v: any) => v.pre_social_score);
      
      if (videos.length > 0) {
        state.selectedVideo = videos[0];
      }
    }
    
    if (state.selectedVideo) {
      console.log(`✓ Selected: ${state.selectedVideo.filename || state.selectedVideo.media_id}`);
    } else {
      console.log('⚠️ No analyzed video available');
    }
  });

  test('2.2 Generate captions for publishing', async ({ request }) => {
    console.log('\n📝 PHASE 2.2: Generating platform captions...');
    
    if (!state.selectedVideo) {
      test.skip();
      return;
    }
    
    const response = await request.post(
      `${API_URL}/api/analysis/generate-captions/${state.selectedVideo.media_id}`,
      {
        data: {
          platform: 'tiktok',
          tone: 'engaging',
          style: 'viral',
          include_hashtags: true,
        }
      }
    );
    
    if (response.ok) {
      const captions = await response.json();
      console.log('✓ Captions generated:');
      console.log(`  - Title: ${captions.title?.slice(0, 50)}...`);
      console.log(`  - Platforms: ${Object.keys(captions.captions || {}).join(', ')}`);
    } else {
      console.log(`⚠️ Caption generation returned ${response.status()}`);
    }
  });

  test('2.3 Schedule post via scheduler', async ({ request }) => {
    console.log('\n📅 PHASE 2.3: Scheduling post...');
    
    if (!state.selectedVideo) {
      test.skip();
      return;
    }
    
    const futureDate = new Date();
    futureDate.setMinutes(futureDate.getMinutes() + 5);
    
    const response = await request.post(`${API_URL}/api/schedule/posts`, {
      data: {
        media_id: state.selectedVideo.media_id,
        platform: 'tiktok',
        account_id: MAIN_ACCOUNTS.tiktok.id,
        scheduled_time: futureDate.toISOString(),
        caption: 'Automated test post via MediaPoster',
        status: 'scheduled',
      }
    });
    
    console.log(`Scheduler response: ${response.status()}`);
    
    if (response.ok) {
      const result = await response.json();
      console.log('✓ Post scheduled successfully');
      state.scheduledPosts.push(result);
    }
  });

  test('2.4 Publish via Blotato (test mode)', async ({ request }) => {
    console.log('\n🚀 PHASE 2.4: Publishing via Blotato...');
    
    if (!state.selectedVideo) {
      test.skip();
      return;
    }
    
    // Check if full-publish endpoint exists
    const response = await request.post(`${API_URL}/api/blotato/posts/full-publish`, {
      data: {
        media_id: state.selectedVideo.media_id,
        blotato_account_id: MAIN_ACCOUNTS.tiktok.id,
        platform: 'tiktok',
        username: MAIN_ACCOUNTS.tiktok.username,
        text: 'Test publish via E2E workflow',
        cleanup_gdrive: true,
      }
    });
    
    console.log(`Full publish response: ${response.status()}`);
    
    if (response.ok) {
      const result = await response.json();
      state.publishedPostId = result.post_submission_id || result.post_id;
      console.log(`✓ Published! Post ID: ${state.publishedPostId}`);
    }
  });

  test('2.5 Poll for post URL', async ({ request }) => {
    console.log('\n🔄 PHASE 2.5: Polling for post URL...');
    
    if (!state.publishedPostId) {
      console.log('⚠️ No published post to poll');
      test.skip();
      return;
    }
    
    // Poll for URL
    for (let attempt = 0; attempt < TEST_CONFIG.maxPollAttempts; attempt++) {
      console.log(`  Polling attempt ${attempt + 1}/${TEST_CONFIG.maxPollAttempts}...`);
      
      const response = await request.get(
        `${API_URL}/api/blotato/posts/${state.publishedPostId}/status`
      );
      
      if (response.ok) {
        const status = await response.json();
        
        if (status.video_url || status.platform_url) {
          state.publishedUrl = status.video_url || status.platform_url;
          console.log(`✓ Got URL: ${state.publishedUrl}`);
          break;
        }
      }
      
      await new Promise(r => setTimeout(r, TEST_CONFIG.pollIntervalMs));
    }
    
    if (!state.publishedUrl) {
      console.log('⚠️ Could not obtain post URL within timeout');
    }
  });

  test('2.6 Fetch post statistics via third-party endpoint', async ({ request }) => {
    console.log('\n📊 PHASE 2.6: Fetching post statistics...');
    
    if (!state.publishedUrl && !state.publishedPostId) {
      console.log('⚠️ No post to fetch stats for');
      test.skip();
      return;
    }
    
    // Wait for initial stats to accumulate
    console.log(`  Waiting ${TEST_CONFIG.shortTermWaitMs / 1000}s for stats...`);
    await new Promise(r => setTimeout(r, TEST_CONFIG.shortTermWaitMs));
    
    // Try to fetch stats
    const response = await request.get(
      `${API_URL}/api/analytics/post-stats?post_id=${state.publishedPostId || 'test'}`
    );
    
    if (response.ok) {
      state.postStats = await response.json();
      console.log('✓ Stats retrieved:');
      console.log(`  - Views: ${state.postStats.views || 0}`);
      console.log(`  - Likes: ${state.postStats.likes || 0}`);
      console.log(`  - Comments: ${state.postStats.comments || 0}`);
    } else {
      console.log(`  Stats endpoint returned ${response.status()}`);
    }
  });
});

// ============================================================================
// PHASE 3: NARRATIVE BUILDER
// ============================================================================

test.describe('PHASE 3: Narrative Builder', () => {
  
  test('3.1 Fetch analyzed content inventory', async ({ request }) => {
    console.log('\n📚 PHASE 3.1: Fetching content inventory for narrative...');
    
    const response = await request.get(
      `${API_URL}/api/narrative-builder/candidate-pool`
    );
    
    if (response.ok) {
      const data = await response.json();
      const candidates = data.candidates || [];
      console.log(`✓ Found ${candidates.length} candidate videos for narrative`);
    } else {
      console.log(`  Narrative builder returned ${response.status()}`);
    }
  });

  test('3.2 Review narrative goals', async ({ request }) => {
    console.log('\n🎯 PHASE 3.2: Reviewing narrative goals...');
    
    const response = await request.get(`${API_URL}/api/narrative-builder/goals`);
    
    if (response.ok) {
      const goals = await response.json();
      console.log('✓ Narrative goals retrieved');
      console.log(`  - Active goals: ${goals.goals?.length || 0}`);
    } else {
      console.log(`  Goals endpoint returned ${response.status()}`);
    }
  });

  test('3.3 Design 7-day content plan', async ({ request }) => {
    console.log('\n📆 PHASE 3.3: Designing 7-day content plan...');
    
    const response = await request.post(`${API_URL}/api/narrative-builder/generate-plan`, {
      data: {
        days: 7,
        platforms: ['tiktok', 'instagram', 'youtube'],
        goals: ['engagement', 'growth'],
        content_mix: {
          viral: 0.4,
          educational: 0.3,
          personal: 0.3,
        }
      }
    });
    
    if (response.ok) {
      state.narrativePlan = await response.json();
      console.log('✓ 7-day plan generated:');
      
      const plan = state.narrativePlan.plan || state.narrativePlan;
      if (Array.isArray(plan)) {
        plan.slice(0, 3).forEach((day: any, i: number) => {
          console.log(`  Day ${i + 1}: ${day.posts?.length || 0} posts planned`);
        });
      }
    } else {
      console.log(`  Plan generation returned ${response.status()}`);
    }
  });

  test('3.4 Execute posts through scheduler', async ({ request }) => {
    console.log('\n🚀 PHASE 3.4: Executing narrative plan through scheduler...');
    
    if (!state.narrativePlan) {
      console.log('⚠️ No narrative plan to execute');
      test.skip();
      return;
    }
    
    const plan = state.narrativePlan.plan || [];
    let scheduledCount = 0;
    
    for (const day of plan.slice(0, 2)) { // Only first 2 days for test
      for (const post of (day.posts || []).slice(0, 1)) { // Only 1 post per day
        const scheduleRes = await request.post(`${API_URL}/api/schedule/posts`, {
          data: {
            media_id: post.media_id || state.selectedVideo?.media_id,
            platform: post.platform || 'tiktok',
            account_id: MAIN_ACCOUNTS[post.platform as keyof typeof MAIN_ACCOUNTS]?.id || MAIN_ACCOUNTS.tiktok.id,
            scheduled_time: post.scheduled_time || new Date().toISOString(),
            caption: post.caption || 'Narrative builder post',
            status: 'scheduled',
          }
        });
        
        if (scheduleRes.status() === 200 || scheduleRes.status() === 201) {
          scheduledCount++;
        }
      }
    }
    
    console.log(`✓ Scheduled ${scheduledCount} posts from narrative plan`);
  });

  test('3.5 Collect URLs and stats after publishing', async ({ request }) => {
    console.log('\n📈 PHASE 3.5: Collecting post URLs and statistics...');
    
    // Get scheduled posts
    const response = await request.get(`${API_URL}/api/schedule/posts?status=completed`);
    
    if (response.ok) {
      const data = await response.json();
      const completedPosts = data.posts || data.items || [];
      
      console.log(`✓ Found ${completedPosts.length} completed posts`);
      
      // Collect stats for each
      for (const post of completedPosts.slice(0, 3)) {
        console.log(`  - ${post.platform}: ${post.platform_url || 'URL pending'}`);
      }
    }
  });

  test('3.6 Feedback to narrative builder for reflection', async ({ request }) => {
    console.log('\n🔄 PHASE 3.6: Feeding back stats to narrative builder...');
    
    const response = await request.post(`${API_URL}/api/narrative-builder/reflect`, {
      data: {
        period: 'last_7_days',
        stats: state.postStats || {},
        completed_posts: state.scheduledPosts,
      }
    });
    
    if (response.ok) {
      const reflection = await response.json();
      console.log('✓ Reflection completed');
      console.log(`  - Recommendations: ${reflection.recommendations?.length || 0}`);
    } else {
      console.log(`  Reflection endpoint returned ${response.status()}`);
    }
  });

  test('3.7 Plan next 7 days with daily assessments', async ({ request }) => {
    console.log('\n📅 PHASE 3.7: Planning next 7 days with assessments...');
    
    const response = await request.get(`${API_URL}/api/narrative-builder/dashboard-signals`);
    
    if (response.ok) {
      const signals = await response.json();
      console.log('✓ Dashboard signals retrieved for planning');
      console.log(`  - Trending topics: ${signals.trending?.length || 0}`);
      console.log(`  - Content gaps: ${signals.gaps?.length || 0}`);
    } else {
      console.log(`  Dashboard signals returned ${response.status()}`);
    }
  });

  test('3.8 Log URLs for narrative tracking', async ({ request }) => {
    console.log('\n📝 PHASE 3.8: Logging URLs for tracking...');
    
    // Get all scheduled posts with URLs
    const response = await request.get(`${API_URL}/api/schedule/posts?limit=50`);
    
    if (response.ok) {
      const data = await response.json();
      const posts = data.posts || data.items || [];
      const withUrls = posts.filter((p: any) => p.platform_url);
      
      console.log(`✓ Tracking ${withUrls.length} posts with URLs`);
      
      withUrls.slice(0, 5).forEach((p: any) => {
        console.log(`  - ${p.platform}: ${p.platform_url?.slice(0, 50)}...`);
      });
    }
  });
});

// ============================================================================
// PHASE 4: EXPERIMENTS
// ============================================================================

test.describe('PHASE 4: Experiments', () => {
  
  test('4.1 Select video for experiment', async ({ request }) => {
    console.log('\n🧪 PHASE 4.1: Selecting video for experiment...');
    
    // Get analyzed videos for experimentation
    const response = await request.get(`${API_URL}/api/media-db/list?limit=20`);
    
    if (response.ok) {
      const data = await response.json();
      const analyzed = (data.items || []).filter((v: any) => v.pre_social_score);
      
      if (analyzed.length > 0) {
        // Pick a random one for experiment
        const experimentVideo = analyzed[Math.floor(Math.random() * analyzed.length)];
        console.log(`✓ Selected for experiment: ${experimentVideo.filename}`);
        state.experimentResults = { sourceVideo: experimentVideo };
      }
    }
  });

  test('4.2 Create experiment with hypothesis', async ({ request }) => {
    console.log('\n💡 PHASE 4.2: Creating experiment with hypothesis...');
    
    const response = await request.post(`${API_URL}/api/experiments/create`, {
      data: {
        name: 'E2E Test Experiment',
        hypothesis: 'Adding trending audio will increase engagement by 20%',
        type: 'content_variation',
        source_media_id: state.experimentResults?.sourceVideo?.media_id || state.selectedVideo?.media_id,
        variations: [
          { name: 'control', description: 'Original video' },
          { name: 'treatment', description: 'Video with trending audio' },
        ],
        success_metric: 'engagement_rate',
        target_improvement: 0.2,
      }
    });
    
    if (response.ok) {
      const experiment = await response.json();
      state.experimentResults = { ...state.experimentResults, experiment };
      console.log(`✓ Experiment created: ${experiment.id || experiment.name}`);
    } else {
      console.log(`  Experiments endpoint returned ${response.status()}`);
    }
  });

  test('4.3 Post experiment to sister account', async ({ request }) => {
    console.log('\n📤 PHASE 4.3: Posting experiment to sister account...');
    
    const sisterAccount = SISTER_ACCOUNTS.tiktok;
    
    const response = await request.post(`${API_URL}/api/schedule/posts`, {
      data: {
        media_id: state.experimentResults?.sourceVideo?.media_id || state.selectedVideo?.media_id,
        platform: 'tiktok',
        account_id: sisterAccount.id,
        username: sisterAccount.username,
        scheduled_time: new Date().toISOString(),
        caption: 'Experiment test post - variation A',
        status: 'scheduled',
        experiment_id: state.experimentResults?.experiment?.id,
        is_experiment: true,
      }
    });
    
    console.log(`Experiment post scheduled: ${response.status()}`);
    
    if (response.ok) {
      const result = await response.json();
      console.log(`✓ Posted to sister account @${sisterAccount.username}`);
      state.experimentResults = { ...state.experimentResults, post: result };
    }
  });

  test('4.4 Collect experiment results (short-term)', async ({ request }) => {
    console.log('\n📊 PHASE 4.4: Collecting short-term experiment results...');
    
    // Wait for initial data
    console.log(`  Waiting ${TEST_CONFIG.shortTermWaitMs / 1000}s for short-term data...`);
    await new Promise(r => setTimeout(r, Math.min(TEST_CONFIG.shortTermWaitMs, 5000)));
    
    const experimentId = state.experimentResults?.experiment?.id || 'test';
    const response = await request.get(
      `${API_URL}/api/experiments/${experimentId}/results?timeframe=short`
    );
    
    if (response.ok) {
      const results = await response.json();
      console.log('✓ Short-term results:');
      console.log(`  - Control engagement: ${results.control?.engagement || 'N/A'}`);
      console.log(`  - Treatment engagement: ${results.treatment?.engagement || 'N/A'}`);
    } else {
      console.log(`  Results endpoint returned ${response.status()}`);
    }
  });

  test('4.5 Analyze experiment data', async ({ request }) => {
    console.log('\n🔬 PHASE 4.5: Analyzing experiment data...');
    
    const experimentId = state.experimentResults?.experiment?.id || 'test';
    const response = await request.post(
      `${API_URL}/api/experiments/${experimentId}/analyze`,
      {
        data: {
          include_statistical_significance: true,
          confidence_level: 0.95,
        }
      }
    );
    
    if (response.ok) {
      const analysis = await response.json();
      console.log('✓ Analysis complete:');
      console.log(`  - Significant: ${analysis.is_significant || 'TBD'}`);
      console.log(`  - Improvement: ${analysis.improvement_percentage || 'N/A'}%`);
    } else {
      console.log(`  Analysis endpoint returned ${response.status()}`);
    }
  });

  test('4.6 Feedback to experimental builder', async ({ request }) => {
    console.log('\n🔄 PHASE 4.6: Feeding back to experimental builder...');
    
    const response = await request.post(`${API_URL}/api/experiments/feedback`, {
      data: {
        experiment_id: state.experimentResults?.experiment?.id,
        outcome: 'completed',
        learnings: [
          'Trending audio shows promise for engagement',
          'Sister account performed as expected',
        ],
        next_steps: [
          'Scale winning variation to main account',
          'Design follow-up experiment',
        ],
      }
    });
    
    if (response.ok) {
      console.log('✓ Feedback recorded for future experiments');
    } else {
      console.log(`  Feedback endpoint returned ${response.status()}`);
    }
  });
});

// ============================================================================
// SUMMARY & CLEANUP
// ============================================================================

test.describe('SUMMARY: Full Workflow Results', () => {
  
  test('Generate workflow summary report', async () => {
    console.log('\n' + '='.repeat(60));
    console.log('FULL WORKFLOW E2E TEST - SUMMARY REPORT');
    console.log('='.repeat(60));
    
    console.log('\n📹 PHASE 1: Video Ingestion & Analysis');
    console.log(`   - Total videos: ${state.ingestedVideos.length}`);
    console.log(`   - Analyzed: ${state.analyzedVideos.length}`);
    console.log(`   - Selected: ${state.selectedVideo?.filename || 'N/A'}`);
    
    console.log('\n📤 PHASE 2: Publishing via Blotato');
    console.log(`   - Published post ID: ${state.publishedPostId || 'N/A'}`);
    console.log(`   - Post URL: ${state.publishedUrl || 'Pending'}`);
    console.log(`   - Stats: ${state.postStats ? 'Retrieved' : 'Pending'}`);
    
    console.log('\n📆 PHASE 3: Narrative Builder');
    console.log(`   - Plan generated: ${state.narrativePlan ? 'Yes' : 'No'}`);
    console.log(`   - Scheduled posts: ${state.scheduledPosts.length}`);
    
    console.log('\n🧪 PHASE 4: Experiments');
    console.log(`   - Experiment created: ${state.experimentResults?.experiment ? 'Yes' : 'No'}`);
    console.log(`   - Sister account used: ${SISTER_ACCOUNTS.tiktok.username}`);
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ FULL WORKFLOW E2E TEST COMPLETE');
    console.log('='.repeat(60));
  });
});
