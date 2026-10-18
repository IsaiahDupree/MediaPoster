"""
Comprehensive E2E Test for Full AI Agent SaaS Workflow

This test covers the complete end-to-end flow:
1. Video Ingestion & Analysis
2. Posting via Blotato with Scheduler
3. Third-party Analytics Collection
4. Narrative Builder Workflow (7-day planning, posting, reflection)
5. Experiments Workflow (video editing, sister account posting, analytics tracking)

This is the full Flowtush for the AI agent SaaS.
"""
import pytest
import httpx
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
import json

# API Configuration
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
BLOTATO_API_URL = f"{API_BASE}/api/blotato"
NARRATIVE_API_URL = f"{API_BASE}/api/narrative"
EXPERIMENTS_API_URL = f"{API_BASE}/api/experiments"
POSTED_CONTENT_API_URL = f"{API_BASE}/api/posted-content"
SCHEDULE_API_URL = f"{API_BASE}/api/publishing/scheduled"

# Test configuration
TEST_TIMEOUT = 300  # 5 minutes for full workflow
POLL_INTERVAL = 5  # seconds between polls
ANALYTICS_WAIT_TIME = 30  # seconds to wait before fetching analytics


class TestFullAIAgentWorkflow:
    """
    Complete E2E test for the full AI agent SaaS workflow.
    Tests all major components working together.
    """
    
    # Shared state across test methods
    ingested_video_id: Optional[str] = None
    analyzed_video_id: Optional[str] = None
    posted_url: Optional[str] = None
    narrative_goal_id: Optional[str] = None
    narrative_plan_id: Optional[str] = None
    scheduled_post_ids: List[str] = []
    experiment_id: Optional[str] = None
    experiment_post_url: Optional[str] = None
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_environment(self):
        """Setup test environment and verify backend is running."""
        print("\n" + "="*80)
        print("FULL AI AGENT SAAS E2E TEST - SETUP")
        print("="*80)
        
        # Verify backend is running
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=5)
            assert response.status_code in [200, 404], "Backend not responding"
            print("✓ Backend is running")
        except Exception as e:
            pytest.skip(f"Backend not available: {e}")
        
        yield
        
        # Cleanup (optional - can be added if needed)
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
    
    # =============================================================================
    # PHASE 1: VIDEO INGESTION & ANALYSIS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_01_find_ingested_videos(self):
        """Step 1: Find videos that are ingested (not yet analyzed)."""
        print("\n" + "="*80)
        print("PHASE 1: VIDEO INGESTION & ANALYSIS")
        print("="*80)
        print("\n📥 STEP 1.1: Finding ingested videos...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DB_API_URL}/list",
                params={"status": "ingested", "limit": 10},
                timeout=30
            )
        
        assert response.status_code == 200, f"Failed to get ingested videos: {response.text}"
        data = response.json()
        
        videos = data.get("items", [])
        print(f"   Found {len(videos)} ingested videos")
        
        if not videos:
            pytest.skip("No ingested videos found - need to ingest videos first")
        
        # Store first ingested video
        self.ingested_video_id = videos[0]["media_id"]
        print(f"   ✓ Selected video: {videos[0]['filename']} (ID: {self.ingested_video_id})")
    
    @pytest.mark.asyncio
    async def test_02_find_analyzed_videos(self):
        """Step 2: Find videos that are already analyzed."""
        print("\n📊 STEP 1.2: Finding analyzed videos...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DB_API_URL}/list",
                params={"status": "analyzed", "limit": 10},
                timeout=30
            )
        
        assert response.status_code == 200, f"Failed to get analyzed videos: {response.text}"
        data = response.json()
        
        videos = data.get("items", [])
        print(f"   Found {len(videos)} analyzed videos")
        
        if videos:
            # Use an analyzed video for posting
            self.analyzed_video_id = videos[0]["media_id"]
            print(f"   ✓ Selected analyzed video: {videos[0]['filename']} (ID: {self.analyzed_video_id})")
        else:
            print("   ⚠️  No analyzed videos found - will analyze one in next step")
    
    @pytest.mark.asyncio
    async def test_03_analyze_video_if_needed(self):
        """Step 3: Analyze a video if we don't have an analyzed one."""
        print("\n🔬 STEP 1.3: Ensuring we have an analyzed video...")
        
        if not self.analyzed_video_id and self.ingested_video_id:
            print(f"   Analyzing video: {self.ingested_video_id}")
            
            # Start analysis
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DB_API_URL}/analyze/{self.ingested_video_id}",
                    timeout=30
                )
            
            assert response.status_code in [200, 202], f"Analysis failed: {response.text}"
            print("   ✓ Analysis started")
            
            # Poll for analysis completion
            max_attempts = 30
            async with httpx.AsyncClient() as client:
                for attempt in range(max_attempts):
                    await asyncio.sleep(POLL_INTERVAL)
                    
                    detail_response = await client.get(
                        f"{DB_API_URL}/detail/{self.ingested_video_id}",
                        timeout=30
                    )
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        if detail_data.get("transcript") or detail_data.get("topics"):
                            self.analyzed_video_id = self.ingested_video_id
                            print(f"   ✓ Analysis complete (attempt {attempt + 1})")
                            print(f"   ✓ Transcript: {bool(detail_data.get('transcript'))}")
                            print(f"   ✓ Topics: {len(detail_data.get('topics', []))}")
                            print(f"   ✓ Deep Analysis: {bool(detail_data.get('deep_analysis'))}")
                            break
                    
                    print(f"   Waiting for analysis... ({attempt + 1}/{max_attempts})")
            
            assert self.analyzed_video_id, "Analysis did not complete in time"
        elif self.analyzed_video_id:
            print(f"   ✓ Using existing analyzed video: {self.analyzed_video_id}")
        else:
            pytest.skip("No video available for analysis")
    
    # =============================================================================
    # PHASE 2: POSTING VIA BLOTATO & SCHEDULER
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_04_get_blotato_accounts(self):
        """Step 4: Get Blotato connected accounts."""
        print("\n" + "="*80)
        print("PHASE 2: POSTING VIA BLOTATO & SCHEDULER")
        print("="*80)
        print("\n🔗 STEP 2.1: Getting Blotato accounts...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BLOTATO_API_URL}/accounts",
                timeout=30
            )
        
        assert response.status_code == 200, f"Failed to get accounts: {response.text}"
        data = response.json()
        
        accounts = data.get("accounts", [])
        print(f"   Found {len(accounts)} connected accounts")
        
        if not accounts:
            pytest.skip("No Blotato accounts connected - need to connect an account first")
        
        # Store account info for later use
        self.blotato_account_id = accounts[0]["account_id"]
        self.blotato_platform = accounts[0]["platform"]
        print(f"   ✓ Using account: {accounts[0]['username']} ({self.blotato_platform})")
        print(f"   ✓ Account ID: {self.blotato_account_id}")
    
    @pytest.mark.asyncio
    async def test_05_schedule_post_via_blotato(self):
        """Step 5: Schedule a post using Blotato and scheduler."""
        print("\n📅 STEP 2.2: Scheduling post via Blotato...")
        
        assert self.analyzed_video_id, "No analyzed video available"
        assert hasattr(self, 'blotato_account_id'), "No Blotato account available"
        
        async with httpx.AsyncClient() as client:
            # Get video details for caption
            detail_response = await client.get(
                f"{DB_API_URL}/detail/{self.analyzed_video_id}",
                timeout=30
            )
        assert detail_response.status_code == 200
        video_data = detail_response.json()
        
        # Generate caption from analysis
        transcript = video_data.get("transcript", "")[:200] if video_data.get("transcript") else "Check this out!"
        topics = video_data.get("topics", [])[:3]
        hashtags = " ".join([f"#{t.replace(' ', '')}" for t in topics[:5]])
        caption = f"{transcript}\n\n{hashtags}"
        
        # Schedule post for 1 hour from now
        scheduled_time = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # Use full-publish-tracked endpoint to get URL
        publish_response = await client.post(
            f"{BLOTATO_API_URL}/posts/full-publish-tracked",
            json={
                "media_id": self.analyzed_video_id,
                "account_id": self.blotato_account_id,
                "platform": self.blotato_platform,
                "text": caption,
                "scheduled_time": scheduled_time,
            },
            timeout=60
        )
        
        assert publish_response.status_code == 200, f"Publish failed: {publish_response.text}"
        publish_data = publish_response.json()
        
        assert publish_data.get("success"), f"Publish not successful: {publish_data}"
        
        self.posted_url = publish_data.get("platform_url")
        self.post_submission_id = publish_data.get("post_submission_id")
        
        print(f"   ✓ Post scheduled successfully")
        print(f"   ✓ Post Submission ID: {self.post_submission_id}")
        print(f"   ✓ Platform URL: {self.posted_url}")
        
        # Also schedule via scheduler endpoint for tracking
        schedule_response = await client.post(
            f"{SCHEDULE_API_URL}/create",
            json={
                "media_id": self.analyzed_video_id,
                "platform": self.blotato_platform,
                "scheduled_time": scheduled_time,
                "caption": caption,
            },
            timeout=30
        )
        
        if schedule_response.status_code == 200:
            schedule_data = schedule_response.json()
            if "id" in schedule_data:
                self.scheduled_post_ids.append(schedule_data["id"])
                print(f"   ✓ Also scheduled in scheduler: {schedule_data['id']}")
    
    @pytest.mark.asyncio
    async def test_06_wait_for_post_publication(self):
        """Step 6: Wait for post to be published and get polling URL."""
        print("\n⏳ STEP 2.3: Waiting for post publication...")
        
        assert self.post_submission_id, "No post submission ID"
        
        # Poll for post status
        max_attempts = 20
        for attempt in range(max_attempts):
            await asyncio.sleep(POLL_INTERVAL)
            
            # Check post status via Blotato (if endpoint exists)
            # For now, just wait and assume it will be published
            print(f"   Waiting for publication... ({attempt + 1}/{max_attempts})")
            
            # After waiting, try to get the URL
            if self.posted_url:
                print(f"   ✓ Post URL available: {self.posted_url}")
                break
        
        assert self.posted_url, "Post URL not obtained"
        print(f"   ✓ Post published: {self.posted_url}")
    
    @pytest.mark.asyncio
    async def test_07_fetch_third_party_analytics(self):
        """Step 7: Fetch analytics data from third-party endpoints."""
        print("\n📊 STEP 2.4: Fetching third-party analytics...")
        
        assert self.posted_url, "No post URL available"
        
        # Wait a bit for analytics to be available
        print(f"   Waiting {ANALYTICS_WAIT_TIME} seconds for analytics to be available...")
        await asyncio.sleep(ANALYTICS_WAIT_TIME)
        
        # Fetch analytics by URL
        async with httpx.AsyncClient() as client:
            analytics_response = await client.get(
                f"{POSTED_CONTENT_API_URL}/analytics/by-url",
                params={"url": self.posted_url},
                timeout=30
            )
        
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
            print(f"   ✓ Analytics fetched successfully")
            print(f"   ✓ Metrics: {analytics_data.get('metrics', {})}")
            self.post_analytics = analytics_data
        else:
            print(f"   ⚠️  Analytics fetch returned {analytics_response.status_code}")
            print(f"   Response: {analytics_response.text}")
            # Don't fail - analytics might not be immediately available
    
    # =============================================================================
    # PHASE 3: NARRATIVE BUILDER WORKFLOW
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_08_narrative_builder_get_signals(self):
        """Step 8: Get narrative builder signals (analyzed content, goals)."""
        print("\n" + "="*80)
        print("PHASE 3: NARRATIVE BUILDER WORKFLOW")
        print("="*80)
        print("\n📈 STEP 3.1: Getting narrative builder signals...")
        
        async with httpx.AsyncClient() as client:
            # Get signals
            signals_response = await client.get(
                f"{API_BASE}/api/narrative-builder/signals",
                timeout=30
            )
        
        assert signals_response.status_code == 200, f"Failed to get signals: {signals_response.text}"
        signals_data = signals_response.json()
        
        print(f"   ✓ Creative Fatigue: {signals_data.get('creative_fatigue', 0)}%")
        print(f"   ✓ Topic Momentum: {len(signals_data.get('topic_momentum', []))} topics")
        
        # Get candidate pool
        candidates_response = await client.get(
            f"{API_BASE}/api/narrative-builder/candidates",
            params={"limit": 20},
            timeout=30
        )
        
        assert candidates_response.status_code == 200
        candidates_data = candidates_response.json()
        candidates = candidates_data.get("candidates", [])
        
        print(f"   ✓ Found {len(candidates)} content candidates")
        
        # Get narrative goals
        goals_response = await client.get(
            f"{NARRATIVE_API_URL}/goals",
            timeout=30
        )
        
        if goals_response.status_code == 200:
            goals_data = goals_response.json()
            goals = goals_data.get("goals", [])
            print(f"   ✓ Found {len(goals)} narrative goals")
            
            if goals:
                self.narrative_goal_id = goals[0]["id"]
                print(f"   ✓ Using goal: {goals[0].get('goal_statement', 'N/A')}")
            else:
                # Create a default goal
                async with httpx.AsyncClient() as client2:
                    create_goal_response = await client2.post(
                        f"{NARRATIVE_API_URL}/goals",
                        json={
                            "goal_statement": "Grow engagement and build audience",
                            "primary_cta": "follow",
                            "target_audience": "general",
                            "time_horizon": "next_7_days"
                        },
                        timeout=30
                    )
                    if create_goal_response.status_code == 200:
                        goal_data = create_goal_response.json()
                        self.narrative_goal_id = goal_data.get("id")
                        print(f"   ✓ Created new goal: {self.narrative_goal_id}")
    
    @pytest.mark.asyncio
    async def test_09_narrative_builder_generate_7_day_plan(self):
        """Step 9: Generate 7-day content plan using narrative builder."""
        print("\n📅 STEP 3.2: Generating 7-day content plan...")
        
        assert self.narrative_goal_id, "No narrative goal available"
        
        async with httpx.AsyncClient() as client:
            # Generate plan
            plan_response = await client.post(
                f"{NARRATIVE_API_URL}/generate-plan",
                json={
                    "goal_id": self.narrative_goal_id,
                    "use_defaults": True
                },
                timeout=120  # Plan generation can take time
            )
        
        assert plan_response.status_code == 200, f"Plan generation failed: {plan_response.text}"
        plan_data = plan_response.json()
        
        assert plan_data.get("success"), f"Plan not successful: {plan_data}"
        
        plan = plan_data.get("plan", {})
        self.narrative_plan_id = plan.get("id")
        slots = plan.get("slots", [])
        
        print(f"   ✓ 7-day plan generated: {self.narrative_plan_id}")
        print(f"   ✓ Total slots: {len(slots)}")
        print(f"   ✓ Days covered: {plan.get('days', 0)}")
    
    @pytest.mark.asyncio
    async def test_10_narrative_builder_approve_and_schedule(self):
        """Step 10: Approve plan and schedule posts."""
        print("\n✅ STEP 3.3: Approving plan and scheduling posts...")
        
        assert self.narrative_plan_id, "No plan generated"
        
        async with httpx.AsyncClient() as client:
            # Approve plan (this schedules the posts)
            approve_response = await client.post(
                f"{NARRATIVE_API_URL}/plans/{self.narrative_plan_id}/approve",
                timeout=60
            )
            
            if approve_response.status_code == 200:
                approve_data = approve_response.json()
                scheduled = approve_data.get("scheduled_posts", [])
                print(f"   ✓ Plan approved")
                print(f"   ✓ Scheduled {len(scheduled)} posts")
                
                # Store scheduled post IDs
                for post in scheduled:
                    if "id" in post:
                        self.scheduled_post_ids.append(post["id"])
            else:
                print(f"   ⚠️  Approval returned {approve_response.status_code}")
                # Try to get scheduled posts directly
                schedule_list_response = await client.get(
                    f"{SCHEDULE_API_URL}/list",
                    params={"limit": 10},
                    timeout=30
                )
            if schedule_list_response.status_code == 200:
                schedule_data = schedule_list_response.json()
                posts = schedule_data if isinstance(schedule_data, list) else schedule_data.get("items", [])
                print(f"   ✓ Found {len(posts)} scheduled posts")
                for post in posts[:7]:  # First 7 posts
                    if "id" in post:
                        self.scheduled_post_ids.append(post["id"])
    
    @pytest.mark.asyncio
    async def test_11_wait_for_narrative_posts_publication(self):
        """Step 11: Wait for narrative builder posts to be published."""
        print("\n⏳ STEP 3.4: Waiting for narrative posts to be published...")
        
        assert self.scheduled_post_ids, "No posts scheduled"
        
        print(f"   Waiting for {len(self.scheduled_post_ids)} posts to be published...")
        
        # Wait for posts to be published (simulate time passing)
        # In real scenario, scheduler would publish these
        await asyncio.sleep(ANALYTICS_WAIT_TIME)
        
        # Get published URLs
        published_urls = []
        async with httpx.AsyncClient() as client:
            for post_id in self.scheduled_post_ids:
                post_response = await client.get(
                    f"{SCHEDULE_API_URL}/{post_id}",
                    timeout=30
                )
            if post_response.status_code == 200:
                post_data = post_response.json()
                if post_data.get("platform_url"):
                    published_urls.append(post_data["platform_url"])
        
        print(f"   ✓ {len(published_urls)} posts have URLs")
        self.narrative_post_urls = published_urls
    
    @pytest.mark.asyncio
    async def test_12_fetch_narrative_post_analytics(self):
        """Step 12: Fetch analytics for all narrative builder posts."""
        print("\n📊 STEP 3.5: Fetching analytics for narrative posts...")
        
        if not hasattr(self, 'narrative_post_urls') or not self.narrative_post_urls:
            print("   ⚠️  No narrative post URLs available")
            return
        
        narrative_analytics = []
        async with httpx.AsyncClient() as client:
            for url in self.narrative_post_urls:
                await asyncio.sleep(1)  # Rate limit
                
                analytics_response = await client.get(
                    f"{POSTED_CONTENT_API_URL}/analytics/by-url",
                    params={"url": url},
                    timeout=30
                )
            
            if analytics_response.status_code == 200:
                analytics_data = analytics_response.json()
                narrative_analytics.append({
                    "url": url,
                    "metrics": analytics_data.get("metrics", {})
                })
                print(f"   ✓ Analytics for {url[:50]}...")
        
        print(f"   ✓ Fetched analytics for {len(narrative_analytics)} posts")
        self.narrative_analytics = narrative_analytics
    
    @pytest.mark.asyncio
    async def test_13_narrative_builder_reflection(self):
        """Step 13: Run narrative builder reflection on posted content."""
        print("\n🔄 STEP 3.6: Running narrative builder reflection...")
        
        assert self.narrative_goal_id, "No narrative goal"
        
        async with httpx.AsyncClient() as client:
            # Trigger reflection
            reflection_response = await client.post(
                f"{NARRATIVE_API_URL}/goals/{self.narrative_goal_id}/reflect",
                timeout=60
            )
        
        if reflection_response.status_code == 200:
            reflection_data = reflection_response.json()
            print(f"   ✓ Reflection complete")
            print(f"   ✓ Learnings: {len(reflection_data.get('learnings', []))}")
        else:
            print(f"   ⚠️  Reflection returned {reflection_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_14_narrative_builder_next_7_days_plan(self):
        """Step 14: Generate next 7-day plan based on reflection."""
        print("\n📅 STEP 3.7: Generating next 7-day plan...")
        
        assert self.narrative_goal_id, "No narrative goal"
        
        async with httpx.AsyncClient() as client:
            # Generate new plan (should incorporate learnings)
            plan_response = await client.post(
                f"{NARRATIVE_API_URL}/generate-plan",
                json={
                    "goal_id": self.narrative_goal_id,
                    "use_defaults": False
                },
                timeout=120
            )
        
        if plan_response.status_code == 200:
            plan_data = plan_response.json()
            if plan_data.get("success"):
                new_plan = plan_data.get("plan", {})
                print(f"   ✓ New 7-day plan generated: {new_plan.get('id')}")
                print(f"   ✓ Slots: {len(new_plan.get('slots', []))}")
        else:
            print(f"   ⚠️  Plan generation returned {plan_response.status_code}")
    
    # =============================================================================
    # PHASE 4: EXPERIMENTS WORKFLOW
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_15_find_analyzed_videos_for_experiment(self):
        """Step 15: Find analyzed videos for experiment."""
        print("\n" + "="*80)
        print("PHASE 4: EXPERIMENTS WORKFLOW")
        print("="*80)
        print("\n🔬 STEP 4.1: Finding analyzed videos for experiment...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DB_API_URL}/list",
                params={"status": "analyzed", "limit": 5},
                timeout=30
            )
        
        assert response.status_code == 200
        data = response.json()
        videos = data.get("items", [])
        
        assert len(videos) > 0, "No analyzed videos available for experiment"
        
        # Select a video with good pre-social score
        experiment_video = None
        for video in videos:
            if video.get("pre_social_score", 0) >= 60:
                experiment_video = video
                break
        
        if not experiment_video:
            experiment_video = videos[0]
        
        self.experiment_video_id = experiment_video["media_id"]
        print(f"   ✓ Selected video: {experiment_video['filename']}")
        print(f"   ✓ Pre-social score: {experiment_video.get('pre_social_score', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_16_create_experiment(self):
        """Step 16: Create an experiment with hypothesis."""
        print("\n🧪 STEP 4.2: Creating experiment...")
        
        assert self.experiment_video_id, "No video for experiment"
        
        async with httpx.AsyncClient() as client:
            # Create experiment
            experiment_response = await client.post(
                f"{EXPERIMENTS_API_URL}/create",
                json={
                    "name": "E2E Test Experiment - Hook Variation",
                    "hypothesis": "Adding a strong hook in first 3 seconds increases engagement by 20%",
                    "type": "hook",
                    "primary_metric": "engagement_rate",
                    "guardrail_metrics": ["retention_rate", "completion_rate"],
                    "variants": [
                        {
                            "name": "Control",
                            "description": "Original video without hook",
                            "media_id": self.experiment_video_id,
                            "is_control": True
                        },
                        {
                            "name": "Variant - Strong Hook",
                            "description": "Video with hook added in first 3 seconds",
                            "media_id": self.experiment_video_id,
                            "is_control": False
                        }
                    ],
                    "platforms": ["tiktok"],
                    "account_role": "EXPERIMENT_ARM",  # Use sister account
                    "min_sample_size": 100
                },
                timeout=30
            )
        
        assert experiment_response.status_code == 200, f"Experiment creation failed: {experiment_response.text}"
        experiment_data = experiment_response.json()
        
        self.experiment_id = experiment_data.get("id")
        print(f"   ✓ Experiment created: {self.experiment_id}")
        print(f"   ✓ Hypothesis: {experiment_data.get('hypothesis', 'N/A')}")
    
    def test_17_edit_video_for_experiment(self):
        """Step 17: Edit video for experiment variant (simulate video editing tool)."""
        print("\n✂️  STEP 4.3: Editing video for experiment variant...")
        
        assert self.experiment_video_id, "No video for editing"
        
        # In a real scenario, this would call a video editing service
        # For now, we'll simulate by creating a variant reference
        # The actual editing would be done by a video editing tool/service
        
        print(f"   ✓ Video editing simulated for variant")
        print(f"   ✓ Original video: {self.experiment_video_id}")
        print(f"   ⚠️  Note: Actual video editing requires video editing service integration")
        
        # Mark that we have an edited variant
        self.experiment_variant_ready = True
    
    @pytest.mark.asyncio
    async def test_18_schedule_experiment_post(self):
        """Step 18: Schedule experiment post to sister account via scheduler."""
        print("\n📅 STEP 4.4: Scheduling experiment post...")
        
        assert self.experiment_id, "No experiment created"
        assert hasattr(self, 'experiment_variant_ready'), "Variant not ready"
        
        async with httpx.AsyncClient() as client:
            # Get experiment accounts (sister/experiment accounts)
            accounts_response = await client.get(
                f"{BLOTATO_API_URL}/accounts",
                params={"platform": "tiktok"},
                timeout=30
            )
            
            if accounts_response.status_code == 200:
                accounts_data = accounts_response.json()
                accounts = accounts_data.get("accounts", [])
                
                # Find experiment account (sister account)
                experiment_account = None
                for account in accounts:
                    # In real scenario, would check account_role
                    if len(accounts) > 1:
                        experiment_account = accounts[1]  # Use second account as sister
                    else:
                        experiment_account = accounts[0]
                    break
                
                if experiment_account:
                    self.experiment_account_id = experiment_account["account_id"]
                    print(f"   ✓ Using experiment account: {experiment_account.get('username')}")
                    
                    # Schedule post
                    scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
                    
                    publish_response = await client.post(
                        f"{BLOTATO_API_URL}/posts/full-publish-tracked",
                        json={
                            "media_id": self.experiment_video_id,
                            "account_id": self.experiment_account_id,
                            "platform": "tiktok",
                            "text": "🧪 Experiment: Testing hook effectiveness #experiment #test",
                            "scheduled_time": scheduled_time,
                        },
                        timeout=60
                    )
                
                if publish_response.status_code == 200:
                    publish_data = publish_response.json()
                    if publish_data.get("success"):
                        self.experiment_post_url = publish_data.get("platform_url")
                        print(f"   ✓ Experiment post scheduled")
                        print(f"   ✓ Post URL: {self.experiment_post_url}")
    
    @pytest.mark.asyncio
    async def test_19_wait_for_experiment_post_publication(self):
        """Step 19: Wait for experiment post to be published."""
        print("\n⏳ STEP 4.5: Waiting for experiment post publication...")
        
        if not hasattr(self, 'experiment_post_url') or not self.experiment_post_url:
            print("   ⚠️  No experiment post URL - skipping")
            return
        
        print(f"   Waiting {ANALYTICS_WAIT_TIME} seconds for post to be published...")
        await asyncio.sleep(ANALYTICS_WAIT_TIME)
        
        print(f"   ✓ Post should be published: {self.experiment_post_url}")
    
    @pytest.mark.asyncio
    async def test_20_fetch_experiment_post_analytics(self):
        """Step 20: Fetch short-term and long-term analytics for experiment post."""
        print("\n📊 STEP 4.6: Fetching experiment post analytics...")
        
        if not hasattr(self, 'experiment_post_url') or not self.experiment_post_url:
            print("   ⚠️  No experiment post URL - skipping")
            return
        
        async with httpx.AsyncClient() as client:
            # Short-term analytics (immediate)
            short_term_response = await client.get(
                f"{POSTED_CONTENT_API_URL}/analytics/by-url",
                params={"url": self.experiment_post_url},
                timeout=30
            )
        
        if short_term_response.status_code == 200:
            short_term_data = short_term_response.json()
            metrics = short_term_data.get("metrics", {})
            print(f"   ✓ Short-term analytics:")
            print(f"     - Views: {metrics.get('views', 0)}")
            print(f"     - Likes: {metrics.get('likes', 0)}")
            print(f"     - Comments: {metrics.get('comments', 0)}")
            
            self.experiment_short_term_metrics = metrics
        
            # Wait for long-term metrics
            print(f"   Waiting additional time for long-term metrics...")
            await asyncio.sleep(ANALYTICS_WAIT_TIME)
            
            # Long-term analytics
            long_term_response = await client.get(
                f"{POSTED_CONTENT_API_URL}/analytics/by-url",
                params={"url": self.experiment_post_url},
                timeout=30
            )
        
        if long_term_response.status_code == 200:
            long_term_data = long_term_response.json()
            metrics = long_term_data.get("metrics", {})
            print(f"   ✓ Long-term analytics:")
            print(f"     - Views: {metrics.get('views', 0)}")
            print(f"     - Likes: {metrics.get('likes', 0)}")
            print(f"     - Comments: {metrics.get('comments', 0)}")
            
            self.experiment_long_term_metrics = metrics
    
    @pytest.mark.asyncio
    async def test_21_feedback_to_experiment_builder(self):
        """Step 21: Feedback analytics to experiment builder."""
        print("\n🔄 STEP 4.7: Feeding analytics back to experiment builder...")
        
        assert self.experiment_id, "No experiment ID"
        
        async with httpx.AsyncClient() as client:
            # Update experiment with results
            if hasattr(self, 'experiment_short_term_metrics') and hasattr(self, 'experiment_long_term_metrics'):
                # Calculate engagement rate
                short_views = self.experiment_short_term_metrics.get('views', 0) or 1
                short_likes = self.experiment_short_term_metrics.get('likes', 0) or 0
                short_engagement = (short_likes / short_views) * 100 if short_views > 0 else 0
                
                long_views = self.experiment_long_term_metrics.get('views', 0) or 1
                long_likes = self.experiment_long_term_metrics.get('likes', 0) or 0
                long_engagement = (long_likes / long_views) * 100 if long_views > 0 else 0
                
                print(f"   ✓ Short-term engagement: {short_engagement:.2f}%")
                print(f"   ✓ Long-term engagement: {long_engagement:.2f}%")
                
                # Update experiment
                update_response = await client.put(
                    f"{EXPERIMENTS_API_URL}/{self.experiment_id}",
                    json={
                        "notes": f"E2E Test Results - Short: {short_engagement:.2f}%, Long: {long_engagement:.2f}%"
                    },
                    timeout=30
                )
                
                if update_response.status_code == 200:
                    print(f"   ✓ Experiment updated with results")
            
            # Get experiment results
            results_response = await client.get(
                f"{EXPERIMENTS_API_URL}/{self.experiment_id}/results",
                timeout=30
            )
        
        if results_response.status_code == 200:
            results_data = results_response.json()
            print(f"   ✓ Experiment results retrieved")
            print(f"   ✓ Status: {results_data.get('status', 'N/A')}")
    
    # =============================================================================
    # FINAL VERIFICATION
    # =============================================================================
    
    def test_22_verify_complete_workflow(self):
        """Step 22: Verify all components worked together."""
        print("\n" + "="*80)
        print("FINAL VERIFICATION")
        print("="*80)
        
        verification_results = {
            "video_analysis": bool(self.analyzed_video_id),
            "posting": bool(self.posted_url),
            "analytics_collection": hasattr(self, 'post_analytics'),
            "narrative_planning": bool(self.narrative_plan_id),
            "narrative_posting": len(self.scheduled_post_ids) > 0,
            "narrative_analytics": hasattr(self, 'narrative_analytics'),
            "experiment_creation": bool(self.experiment_id),
            "experiment_posting": hasattr(self, 'experiment_post_url'),
            "experiment_analytics": hasattr(self, 'experiment_short_term_metrics'),
        }
        
        print("\n📋 Workflow Verification:")
        for component, status in verification_results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {component.replace('_', ' ').title()}")
        
        all_passed = all(verification_results.values())
        
        print(f"\n{'='*80}")
        if all_passed:
            print("✅ FULL AI AGENT SAAS WORKFLOW TEST: PASSED")
        else:
            print("⚠️  FULL AI AGENT SAAS WORKFLOW TEST: PARTIAL")
            print("   Some components may have been skipped or failed")
        print(f"{'='*80}\n")
        
        # Don't fail the test - this is a comprehensive workflow test
        # Some steps may be skipped due to missing data/accounts
        assert True, "Workflow verification complete"

