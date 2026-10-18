"""
Generate Sora Videos with Trend & Review Context

Uses real AI to generate prompts influenced by:
- Recent trend data
- Review insights for AI/Sora content improvements
- Character: @isaiahdupree

Generates 2x videos (Sora max is 20s, so we'll do 2x 12s clips for ~24s total)
"""

import os
import sys
import json
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

load_dotenv()

# Configuration
CHARACTER = "@isaiahdupree"
NUM_VIDEOS = 2
DURATION_SECONDS = 12  # Sora max is 20s, using 12s for faster generation
MODEL = "sora-2"
SIZE = "720x1280"  # Vertical for shorts/reels/tiktok


def get_review_insights() -> dict:
    """Fetch review insights from API."""
    import httpx
    
    try:
        response = httpx.get("http://localhost:5555/api/review/insights", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Could not fetch insights: {e}")
    
    return {"insights": []}


def get_performance_data() -> dict:
    """Load YouTube performance report."""
    report_path = os.path.join(
        os.path.dirname(__file__), 
        "youtube_performance_report.json"
    )
    
    if os.path.exists(report_path):
        with open(report_path) as f:
            return json.load(f)
    
    return {}


def generate_prompts_with_ai(client: OpenAI, context: dict) -> list:
    """
    Use real GPT-4 to generate Sora prompts influenced by data.
    """
    logger.info("🧠 Generating AI-influenced prompts...")
    
    # Build context from insights and performance data
    insights_text = ""
    for insight in context.get("insights", []):
        insights_text += f"- {insight.get('title', '')}: {insight.get('description', '')}\n"
    
    # What's working for AI/Sora content
    working = [
        "AI/Sora content has highest engagement rate",
        "Repeating winning concepts works",
        "Short, punchy content performs well",
        "Tech/AI topics outperform other categories"
    ]
    
    # Areas to improve
    improve = [
        "Add voiceover to AI visuals for better engagement",
        "Test different content angles or hooks",
        "Improve thumbnails for better discovery",
        "Stronger call-to-actions"
    ]
    
    system_prompt = f"""You are an expert at creating Sora AI video generation prompts.

CHARACTER: The main character is {CHARACTER} - a tech-focused creator making content about AI, productivity, and personal branding.

CONTEXT FROM PERFORMANCE DATA:
{insights_text}

WHAT'S WORKING:
{chr(10).join('- ' + w for w in working)}

AREAS TO IMPROVE:
{chr(10).join('- ' + i for i in improve)}

CURRENT TRENDS:
- Cinematic AI visuals are performing well
- Surreal/dreamlike scenes get high engagement  
- Quick pacing and dynamic camera movement
- Tech aesthetic (neon, holographic, futuristic)
- Personal branding content resonates

Your task: Generate 2 unique Sora video prompts that:
1. MUST start with "{CHARACTER}" as the first word
2. Feature the character in a compelling visual scenario
3. Are optimized for 12-second vertical videos (720x1280)
4. Incorporate what's working from the performance data
5. Are visually stunning and shareable
6. Would perform well on TikTok/Reels/Shorts

Format each prompt on its own line, no numbering."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate 2 unique Sora prompts for {CHARACTER} that would perform well based on the trend and review data. Make them visually striking and optimized for short-form vertical video."}
        ],
        max_tokens=1000,
        temperature=0.9
    )
    
    content = response.choices[0].message.content.strip()
    prompts = [p.strip() for p in content.split('\n') if p.strip() and p.strip().startswith(CHARACTER)]
    
    # Ensure we have exactly 2 prompts
    while len(prompts) < 2:
        prompts.append(f"{CHARACTER} walking through a neon-lit futuristic city at night, holographic data streams floating around, cinematic tracking shot, 4K quality")
    
    return prompts[:2]


def submit_to_sora(client: OpenAI, prompt: str, index: int) -> dict:
    """
    Submit prompt to Sora for video generation.
    """
    logger.info(f"\n📹 Submitting Video {index + 1} to Sora...")
    logger.info(f"   Prompt: {prompt[:100]}...")
    logger.info(f"   Model: {MODEL}, Size: {SIZE}, Duration: {DURATION_SECONDS}s")
    
    try:
        video = client.videos.create(
            model=MODEL,
            prompt=prompt,
            size=SIZE,
            seconds=str(DURATION_SECONDS)
        )
        
        logger.success(f"   ✅ Job created: {video.id}")
        logger.info(f"   Status: {video.status}")
        
        return {
            "job_id": video.id,
            "status": video.status,
            "prompt": prompt,
            "model": MODEL,
            "size": SIZE,
            "duration": DURATION_SECONDS,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"   ❌ Failed: {e}")
        return {
            "error": str(e),
            "prompt": prompt
        }


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("🎬 SORA VIDEO GENERATION WITH CONTEXT")
    print(f"   Character: {CHARACTER}")
    print(f"   Videos: {NUM_VIDEOS}x {DURATION_SECONDS}s")
    print("="*80 + "\n")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY not found")
        return
    
    client = OpenAI()
    
    # Step 1: Gather context
    logger.info("📊 Step 1: Gathering context data...")
    insights = get_review_insights()
    perf_data = get_performance_data()
    
    context = {
        "insights": insights.get("insights", []),
        "performance": perf_data
    }
    
    logger.info(f"   Found {len(context['insights'])} insights")
    
    # Step 2: Generate AI-influenced prompts
    logger.info("\n🧠 Step 2: Generating prompts with GPT-4...")
    prompts = generate_prompts_with_ai(client, context)
    
    print("\n" + "-"*80)
    print("📝 GENERATED PROMPTS:")
    print("-"*80)
    for i, prompt in enumerate(prompts):
        print(f"\n{i+1}. {prompt}")
    print("-"*80 + "\n")
    
    # Step 3: Submit to Sora
    logger.info("🚀 Step 3: Submitting to Sora...")
    
    jobs = []
    for i, prompt in enumerate(prompts):
        result = submit_to_sora(client, prompt, i)
        jobs.append(result)
    
    # Step 4: Save results
    output_path = os.path.join(
        os.path.dirname(__file__),
        "sora_generation_jobs.json"
    )
    
    with open(output_path, 'w') as f:
        json.dump({
            "character": CHARACTER,
            "generated_at": datetime.now().isoformat(),
            "context_used": {
                "insights_count": len(context['insights']),
                "performance_data": bool(perf_data)
            },
            "jobs": jobs
        }, f, indent=2)
    
    logger.success(f"\n✅ Jobs saved to: {output_path}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 GENERATION SUMMARY")
    print("="*80)
    
    successful = [j for j in jobs if "job_id" in j]
    failed = [j for j in jobs if "error" in j]
    
    print(f"\n✅ Submitted: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        print("\n📹 Job IDs (use to check status):")
        for job in successful:
            print(f"   • {job['job_id']}")
        
        print("\n💡 To check status, run:")
        print(f"   python -c \"from openai import OpenAI; c=OpenAI(); print(c.videos.retrieve('{successful[0]['job_id']}'))\"")
    
    print("\n" + "="*80 + "\n")
    
    return jobs


if __name__ == "__main__":
    main()
