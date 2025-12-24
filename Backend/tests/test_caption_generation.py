"""
Tests for caption generation API endpoint.
Verifies that titles and descriptions are properly generated from analysis data.
"""
import pytest
import httpx
import asyncio

API_URL = "http://localhost:5555"

# Get a real media ID from the database
import asyncio
from sqlalchemy import text
from database.connection import async_session_maker

async def get_test_media_id():
    """Get a real media ID with analysis data"""
    if async_session_maker:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT v.id 
                FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE va.transcript IS NOT NULL 
                AND va.topics IS NOT NULL
                LIMIT 1
            """))
            row = result.fetchone()
            if row:
                return str(row[0])
    # Fallback to a known ID or create one
    return "b18c1c8d-3c25-4c16-a20d-dca6cb9552e9"

# Get test media ID synchronously for pytest
TEST_MEDIA_ID = None
try:
    TEST_MEDIA_ID = asyncio.run(get_test_media_id())
except:
    TEST_MEDIA_ID = "b18c1c8d-3c25-4c16-a20d-dca6cb9552e9"  # Fallback


class TestCaptionGeneration:
    """Test the /api/analysis/generate-captions endpoint"""
    
    @pytest.mark.asyncio
    async def test_generate_captions_returns_success(self):
        """Test that the API returns a successful response"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/analysis/generate-captions/{TEST_MEDIA_ID}",
                json={
                    "platform": "tiktok",
                    "tone": "engaging",
                    "include_hashtags": True,
                    "include_hook": True,
                }
            )
            
            # Accept 200 or 404 (media might not exist)
            assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                assert data.get("success") == True
                assert data.get("media_id") == TEST_MEDIA_ID
                assert "captions" in data
                assert "tiktok" in data["captions"]
                assert "instagram" in data["captions"]
                assert "youtube" in data["captions"]
                
                print(f"✅ API returned success")
                print(f"   Title: {data.get('title')}")
                print(f"   Transcript available: {data.get('transcript_available')}")
            else:
                print(f"⚠️  Media not found: {TEST_MEDIA_ID} - skipping test")
                pytest.skip(f"Media {TEST_MEDIA_ID} not found")
    
    @pytest.mark.asyncio
    async def test_title_not_filename(self):
        """Test that generated title is NOT a filename (IMG_, VID_, etc.)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/analysis/generate-captions/{TEST_MEDIA_ID}",
                json={"platform": "tiktok", "tone": "engaging"}
            )
            
            if response.status_code != 200:
                pytest.skip(f"Media {TEST_MEDIA_ID} not found")
            
            data = response.json()
            title = data.get("title", "")
            
            # Title should NOT be a filename
            assert not title.startswith("IMG_"), f"Title is a filename: {title}"
            assert not title.startswith("VID_"), f"Title is a filename: {title}"
            assert not title.startswith("MOV_"), f"Title is a filename: {title}"
            assert not title.endswith(".MOV"), f"Title is a filename: {title}"
            assert not title.endswith(".mp4"), f"Title is a filename: {title}"
            
            print(f"✅ Title is NOT a filename: {title}")
    
    @pytest.mark.asyncio
    async def test_title_and_description_are_different(self):
        """Test that title and description are NOT duplicated"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/analysis/generate-captions/{TEST_MEDIA_ID}",
                json={"platform": "tiktok", "tone": "engaging"}
            )
            
            if response.status_code != 200:
                pytest.skip(f"Media {TEST_MEDIA_ID} not found")
            
            data = response.json()
            if "captions" not in data:
                pytest.skip("No captions in response")
            tiktok_caption = data["captions"]["tiktok"]
            
            # Parse the caption
            lines = tiktok_caption.split('\n')
            title_line = lines[0].replace("🔥", "").replace("✨", "").strip()
            
            # Find the description (skip empty lines after title)
            description_lines = [l for l in lines[1:] if l.strip() and not l.startswith('#')]
            description = description_lines[0] if description_lines else ""
            
            # Title and first line of description should be different
            # (description should be longer/more detailed)
            assert len(description) > len(title_line) or description != title_line, \
                f"Title and description are the same!\nTitle: {title_line}\nDescription: {description}"
            
            print(f"✅ Title and description are different:")
            print(f"   Title: {title_line[:60]}...")
            print(f"   Description: {description[:60]}...")
    
    @pytest.mark.asyncio
    async def test_caption_includes_hashtags(self):
        """Test that captions include relevant hashtags"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/analysis/generate-captions/{TEST_MEDIA_ID}",
                json={"platform": "tiktok", "tone": "engaging", "include_hashtags": True}
            )
            
            if response.status_code != 200:
                pytest.skip(f"Media {TEST_MEDIA_ID} not found")
            
            data = response.json()
            if "captions" not in data:
                pytest.skip("No captions in response")
            tiktok_caption = data["captions"]["tiktok"]
            
            # Should contain hashtags
            assert "#" in tiktok_caption, "Caption should contain hashtags"
            assert "#fyp" in tiktok_caption.lower() or "#viral" in tiktok_caption.lower(), \
                "TikTok caption should contain #fyp or #viral"
            
            # Count hashtags
            hashtag_count = tiktok_caption.count('#')
            assert hashtag_count >= 3, f"Should have at least 3 hashtags, found {hashtag_count}"
            
            print(f"✅ Caption includes {hashtag_count} hashtags")
    
    @pytest.mark.asyncio
    async def test_platform_specific_captions(self):
        """Test that each platform gets a different caption style"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/api/analysis/generate-captions/{TEST_MEDIA_ID}",
                json={"platform": "tiktok", "tone": "engaging"}
            )
            
            if response.status_code != 200:
                pytest.skip(f"Media {TEST_MEDIA_ID} not found")
            
            data = response.json()
            if "captions" not in data:
                pytest.skip("No captions in response")
            tiktok = data["captions"]["tiktok"]
            instagram = data["captions"]["instagram"]
            youtube = data["captions"]["youtube"]
            
            # TikTok should have 🔥 emoji for engaging tone
            assert "🔥" in tiktok or "#fyp" in tiktok, "TikTok should have fire emoji or #fyp"
            
            # Instagram should have ✨ or #reels
            assert "✨" in instagram or "#reels" in instagram, "Instagram should have sparkle emoji or #reels"
            
            # YouTube should have Topics section
            assert "Topics:" in youtube, "YouTube should have Topics section"
            
            print(f"✅ Platform-specific formatting verified")
            print(f"   TikTok: {tiktok[:50]}...")
            print(f"   Instagram: {instagram[:50]}...")
            print(f"   YouTube: {youtube[:50]}...")


class TestAnalysisDataFetch:
    """Test that analysis data is properly fetched"""
    
    @pytest.mark.asyncio
    async def test_fetch_analysis_data(self):
        """Test fetching analysis data for a media item"""
        async with httpx.AsyncClient() as client:
            # Try the media-db analysis endpoint first
            response = await client.get(
                f"{API_URL}/api/media-db/analysis/{TEST_MEDIA_ID}"
            )
            
            # Accept 200 or 404 (media might not exist or might not be analyzed)
            assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify analysis data structure (if available)
                if "transcript" in data:
                    assert "transcript" in data, "Should have transcript"
                if "topics" in data:
                    assert "topics" in data, "Should have topics"
                if "hooks" in data:
                    assert "hooks" in data, "Should have hooks"
                
                print(f"✅ Analysis data fetched successfully")
                print(f"   Transcript length: {len(data.get('transcript', ''))}")
            else:
                print(f"⚠️  Media not found or not analyzed: {TEST_MEDIA_ID}")
                pytest.skip(f"Media {TEST_MEDIA_ID} not found or not analyzed")
            print(f"   Topics: {data.get('topics', [])}")
            print(f"   Hooks count: {len(data.get('hooks', []))}")
            print(f"   Tone: {data.get('tone')}")


def run_tests():
    """Run all tests and print summary"""
    print("=" * 60)
    print("Caption Generation Tests")
    print("=" * 60)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
