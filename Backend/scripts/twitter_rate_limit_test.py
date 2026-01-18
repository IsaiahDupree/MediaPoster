#!/usr/bin/env python3
"""
Twitter Rate Limit Stress Test via Blotato
Tests posting limits by generating 100 unique tweets from top content transcripts.
"""

import asyncio
import time
import json
import httpx
from datetime import datetime
from openai import OpenAI
import os

# Configuration
BLOTATO_API_URL = "https://api.blotato.com"
TWITTER_ACCOUNT_ID = "571"  # @soursides_is_sour
BACKEND_URL = "http://localhost:5555"

# Top transcripts for inspiration
TRANSCRIPTS = [
    "If only you knew that everything that you ever wanted was just on the other side of that action that you just took. Why stop now? Why not take the next leap? Why not do the next action? I encourage everybody out there to keep going because you never know when.",
    "I used to think that back in the day that SEO started blogs way back in 2015. Now that SEO is dying, I think I found my new go-to thing for producing money and I think that's ads.",
    "Life, I think it's about trying to keep the main thing the main thing. And that could keep you motivated, spark action, do new things. And keep you inspired.",
    "Today I'm sharing the seven most profitable business automation integrations that businesses are happily paying thousands for right now. These aren't just theoretical ideas, these are proven practical systems I've personally built for dozens of clients.",
    "Here is honestly the start of something incredible because not only does this help you automate everything on social media but you could pair it with other automations that provide factual information as well as make it concise and hard hitting.",
    "Old people used to tell us, hey, go to school, get a job, that's the normal path. Now, the normal path to make decent money is to become an influencer on some media platform, figure out how to become viral.",
    "Like some of these people that are doing AI and automations don't really understand what a back end is. A back end is something you would use to like be the start or end of your AI automations.",
]

# Tweet themes/angles
THEMES = [
    "hot take", "question to audience", "personal story", "tip/advice", 
    "controversial opinion", "motivational", "behind the scenes", "lesson learned",
    "prediction", "observation"
]

class TwitterRateLimitTest:
    def __init__(self):
        self.openai = OpenAI()
        self.results = {
            "started_at": datetime.now().isoformat(),
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "rate_limited": 0,
            "errors": [],
            "timing": [],
            "first_rate_limit_at": None
        }
        
    async def generate_tweets(self, count: int = 100) -> list:
        """Generate unique tweets using AI based on transcripts."""
        print(f"🤖 Generating {count} unique tweets...")
        tweets = []
        
        batch_size = 20
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_count = batch_end - batch_start
            
            prompt = f"""Generate {batch_count} unique, engaging tweets inspired by these content themes:

TRANSCRIPT INSPIRATIONS:
{chr(10).join(f'- {t[:200]}...' for t in TRANSCRIPTS[:5])}

REQUIREMENTS:
- Each tweet must be under 280 characters
- Make each tweet UNIQUE - different angles, hooks, and messages
- Mix of: hot takes, questions, tips, observations, motivational
- Include relevant emojis sparingly
- NO hashtags (we'll add them separately)
- Sound authentic and personal, not corporate
- Topics: AI, automation, content creation, entrepreneurship, personal growth

OUTPUT FORMAT: Return ONLY a JSON array of tweet strings, nothing else.
Example: ["Tweet 1 text here", "Tweet 2 text here", ...]"""

            try:
                response = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a viral Twitter content creator. Output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.95
                )
                
                content = response.choices[0].message.content.strip()
                # Clean up potential markdown
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                batch_tweets = json.loads(content)
                tweets.extend(batch_tweets)
                print(f"  ✅ Generated batch {batch_start//batch_size + 1}: {len(batch_tweets)} tweets")
                
            except Exception as e:
                print(f"  ❌ Batch generation failed: {e}")
                # Fallback: generate simple variations
                for i in range(batch_count):
                    tweets.append(f"Testing automation #{batch_start + i + 1} 🚀 The future of content is here.")
        
        return tweets[:count]
    
    async def post_tweet(self, tweet_text: str, index: int) -> dict:
        """Post a single tweet via Blotato API directly."""
        start_time = time.time()
        
        BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY")
        if not BLOTATO_API_KEY:
            return {"success": False, "elapsed": 0, "index": index, "error": "BLOTATO_API_KEY not set"}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Post directly to Blotato v2 API (text-only tweet)
                payload = {
                    "post": {
                        "accountId": TWITTER_ACCOUNT_ID,
                        "content": {
                            "text": tweet_text,
                            "mediaUrls": [],  # Empty for text-only
                            "platform": "twitter"
                        },
                        "target": {
                            "targetType": "twitter"
                        }
                    }
                }
                
                response = await client.post(
                    "https://backend.blotato.com/v2/posts",
                    headers={
                        "Authorization": f"Bearer {BLOTATO_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    return {"success": True, "elapsed": elapsed, "index": index, "response": response.json()}
                elif response.status_code == 429:
                    return {"success": False, "rate_limited": True, "elapsed": elapsed, "index": index, "error": "Rate limited"}
                else:
                    error_text = response.text[:200]
                    return {"success": False, "elapsed": elapsed, "index": index, "error": f"{response.status_code}: {error_text}"}
                    
        except Exception as e:
            return {"success": False, "elapsed": time.time() - start_time, "index": index, "error": str(e)}
    
    async def run_test(self, tweet_count: int = 100, delay_between: float = 1.0):
        """Run the full rate limit test."""
        print("=" * 60)
        print(f"🐦 Twitter Rate Limit Test - {tweet_count} tweets")
        print(f"📱 Account: {TWITTER_ACCOUNT_ID}")
        print(f"⏱️  Delay between posts: {delay_between}s")
        print("=" * 60)
        
        # Generate tweets
        tweets = await self.generate_tweets(tweet_count)
        print(f"\n✅ Generated {len(tweets)} tweets\n")
        
        # Post tweets
        print("📤 Starting posting test...\n")
        
        for i, tweet in enumerate(tweets):
            self.results["total_attempts"] += 1
            
            result = await self.post_tweet(tweet, i)
            self.results["timing"].append(result.get("elapsed", 0))
            
            if result.get("success"):
                self.results["successful"] += 1
                print(f"  ✅ [{i+1}/{len(tweets)}] Posted in {result['elapsed']:.2f}s")
            elif result.get("rate_limited"):
                self.results["rate_limited"] += 1
                if not self.results["first_rate_limit_at"]:
                    self.results["first_rate_limit_at"] = i + 1
                print(f"  🚫 [{i+1}/{len(tweets)}] RATE LIMITED after {self.results['successful']} successful posts")
            else:
                self.results["failed"] += 1
                self.results["errors"].append({"index": i, "error": result.get("error")})
                print(f"  ❌ [{i+1}/{len(tweets)}] Failed: {result.get('error', 'Unknown')[:50]}")
            
            # Check if we should stop (too many failures or rate limited)
            if self.results["rate_limited"] >= 3:
                print(f"\n🛑 Stopping: Hit rate limit {self.results['rate_limited']} times")
                break
            
            if self.results["failed"] >= 10 and self.results["successful"] == 0:
                print(f"\n🛑 Stopping: Too many failures without success")
                break
            
            # Delay between posts
            if i < len(tweets) - 1:
                await asyncio.sleep(delay_between)
        
        # Final report
        self.results["ended_at"] = datetime.now().isoformat()
        self.print_report()
        
        return self.results
    
    def print_report(self):
        """Print test results."""
        print("\n" + "=" * 60)
        print("📊 RATE LIMIT TEST RESULTS")
        print("=" * 60)
        print(f"Total Attempts:     {self.results['total_attempts']}")
        print(f"Successful Posts:   {self.results['successful']} ✅")
        print(f"Failed Posts:       {self.results['failed']} ❌")
        print(f"Rate Limited:       {self.results['rate_limited']} 🚫")
        
        if self.results["first_rate_limit_at"]:
            print(f"\n⚠️  First rate limit hit at post #{self.results['first_rate_limit_at']}")
        
        if self.results["timing"]:
            avg_time = sum(self.results["timing"]) / len(self.results["timing"])
            print(f"\nAvg post time:      {avg_time:.2f}s")
        
        if self.results["errors"]:
            print(f"\nFirst 3 errors:")
            for err in self.results["errors"][:3]:
                print(f"  - Post {err['index']}: {err['error'][:60]}")
        
        print("=" * 60)


async def main():
    tester = TwitterRateLimitTest()
    
    # Start with 100 tweets, 1 second delay
    results = await tester.run_test(
        tweet_count=100,
        delay_between=1.0  # 1 second between posts
    )
    
    # Save results
    with open("twitter_rate_limit_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Results saved to twitter_rate_limit_results.json")


if __name__ == "__main__":
    asyncio.run(main())
