"""
Seed Dummy Data for Social Media Analytics
Populates the database with mock accounts, posts, and analytics data
to demonstrate the Analytics Dashboard and Check-back Periods features.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from services.social_analytics_service import SocialAnalyticsService
from services.social_analytics_service import SocialAnalyticsService
from sqlalchemy import create_engine, text

async def create_tables():
    print("Creating tables...")
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        sql_path = Path(__file__).parent / "migrations" / "social_media_analytics.sql"
        with open(sql_path, "r") as f:
            sql_content = f.read()
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"Error executing statement: {e}")
            conn.commit()
    print("Tables created.")

async def seed_data():
    print("\n" + "="*80)
    print("🌱 Seeding Dummy Data for Analytics")
    print("="*80)

    # Ensure tables exist
    print("\n0️⃣ Checking/Creating Database Tables...")
    await create_tables()

    service = SocialAnalyticsService()
    
    # 1. Create Mock Accounts
    accounts_data = [
        {
            "platform": "tiktok",
            "username": "creative_studio_demo",
            "full_name": "Creative Studio",
            "bio": "Digital art & tutorials 🎨 | New video every Tuesday",
            "profile_pic_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
            "is_verified": True,
            "is_business": True,
            "followers_base": 15400,
            "growth_rate": 1.02
        },
        {
            "platform": "instagram",
            "username": "creative_studio_official",
            "full_name": "Creative Studio Official",
            "bio": "Behind the scenes of our design process ✨",
            "profile_pic_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
            "is_verified": False,
            "is_business": True,
            "followers_base": 8200,
            "growth_rate": 1.01
        },
        {
            "platform": "youtube",
            "username": "CreativeStudioTV",
            "full_name": "Creative Studio TV",
            "bio": "Long-form tutorials and design reviews",
            "profile_pic_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
            "is_verified": True,
            "is_business": True,
            "followers_base": 25000,
            "growth_rate": 1.005
        }
    ]

    account_ids = {}

    print("\n1️⃣ Creating Accounts...")
    for acc in accounts_data:
        account_id = await service.get_or_create_account(
            platform=acc["platform"],
            username=acc["username"],
            profile_data={
                "full_name": acc["full_name"],
                "bio": acc["bio"],
                "profile_pic_url": acc["profile_pic_url"],
                "is_verified": acc["is_verified"],
                "is_business": acc["is_business"]
            }
        )
        account_ids[acc["platform"]] = account_id
        print(f"   ✅ {acc['platform']}/@{acc['username']} (ID: {account_id})")

    # 2. Generate Daily History (Last 30 days)
    print("\n2️⃣ Generating Daily Analytics History...")
    
    today = date.today()
    
    for platform, account_id in account_ids.items():
        acc_config = next(a for a in accounts_data if a["platform"] == platform)
        current_followers = acc_config["followers_base"]
        
        # Go back 30 days
        for i in range(30, -1, -1):
            day = today - timedelta(days=i)
            
            # Simulate slight growth/fluctuation
            daily_growth = random.uniform(0.999, acc_config["growth_rate"])
            current_followers = int(current_followers * daily_growth)
            
            # Random daily metrics
            posts_today = 1 if random.random() > 0.8 else 0
            
            await service.save_analytics_snapshot(
                account_id=account_id,
                snapshot_date=day,
                analytics_data={
                    "followers_count": current_followers,
                    "following_count": random.randint(100, 500),
                    "posts_count": 100 + (30 - i), # Accumulating posts
                    "total_likes": int(current_followers * 1.5),
                    "total_comments": int(current_followers * 0.05),
                    "total_views": int(current_followers * 5),
                    "total_shares": int(current_followers * 0.1),
                    "engagement_rate": random.uniform(2.5, 8.5),
                    "avg_likes_per_post": int(current_followers * 0.02),
                    "avg_comments_per_post": int(current_followers * 0.001)
                }
            )
        print(f"   ✅ Generated 30 days of history for {platform}")

    # 3. Create Mock Posts & Check-back Data
    print("\n3️⃣ Creating Posts & Check-back Data...")
    
    post_templates = [
        {"title": "How to design a logo", "type": "video", "base_views": 5000},
        {"title": "My workspace tour", "type": "image", "base_views": 3000},
        {"title": "Top 5 design tips", "type": "carousel", "base_views": 8000},
        {"title": "Client horror story", "type": "video", "base_views": 12000},
        {"title": "Photoshop vs Illustrator", "type": "video", "base_views": 6000},
        {"title": "Day in the life", "type": "video", "base_views": 4500},
        {"title": "Color theory basics", "type": "image", "base_views": 3500},
        {"title": "Typography tutorial", "type": "carousel", "base_views": 7000},
    ]

    for platform, account_id in account_ids.items():
        # Create 5-10 posts per platform
        num_posts = random.randint(5, 10)
        
        for i in range(num_posts):
            template = random.choice(post_templates)
            days_ago = random.randint(0, 14)
            posted_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(1, 12))
            
            # Create Post
            post_id = await service.save_post(
                account_id=account_id,
                platform=platform,
                post_data={
                    "post_id": f"mock_{platform}_{i}_{int(posted_at.timestamp())}",
                    "url": f"https://{platform}.com/p/mock{i}",
                    "caption": f"{template['title']} - Check this out! #design #creative",
                    "media_type": template["type"],
                    "thumbnail_url": f"https://picsum.photos/seed/{i}/400/600",
                    "media_url": f"https://example.com/media/{i}",
                    "duration": 60 if template["type"] == "video" else 0,
                    "posted_at": posted_at.isoformat()
                }
            )
            
            # Create Check-back Data (Post Analytics over time)
            # We simulate checkbacks at 1h, 6h, 24h, 72h, 168h if enough time has passed
            checkback_hours = [1, 6, 24, 72, 168]
            base_views = template["base_views"] * (1.5 if platform == "tiktok" else 1.0)
            
            for hours in checkback_hours:
                checkback_time = posted_at + timedelta(hours=hours)
                
                if checkback_time < datetime.now():
                    # Calculate progressive metrics
                    progress = hours / 168.0 # Simple linear progression for mock data
                    # Logarithmic-ish curve
                    curve = progress ** 0.5 
                    
                    current_views = int(base_views * curve * random.uniform(0.8, 1.2))
                    current_likes = int(current_views * 0.1)
                    current_comments = int(current_views * 0.01)
                    
                    await service.save_post_analytics(
                        post_id=post_id,
                        snapshot_date=checkback_time.date(),
                        analytics_data={
                            "views": current_views,
                            "likes": current_likes,
                            "comments": current_comments,
                            "shares": int(current_views * 0.02),
                            "saves": int(current_views * 0.03)
                        }
                    )
        
        print(f"   ✅ Created {num_posts} posts for {platform}")

    print("\n" + "="*80)
    print("✅ SEEDING COMPLETE")
    print("="*80)
    print("You can now check the Analytics Dashboard and Check-back Periods page.")

if __name__ == "__main__":
    asyncio.run(seed_data())
