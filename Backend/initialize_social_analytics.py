"""
Initialize Social Media Analytics System
- Creates database tables
- Adds monitored accounts
- Fetches initial data
"""
import asyncio
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from services.fetch_social_analytics import fetch_single_account
from services.social_analytics_service import SocialAnalyticsService
from sqlalchemy import create_engine
import os


async def create_database_tables():
    """Create all required database tables"""
    print("\n📋 Creating database tables...")
    
    try:
        # Create direct database connection
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(database_url)
        db = engine.connect()
        
        # Read SQL migration file
        sql_file = Path(__file__).parent / "migrations" / "social_media_analytics.sql"
        
        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL (execute statements one by one)
        from sqlalchemy import text
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        for statement in statements:
            try:
                db.execute(text(statement))
            except Exception as e:
                # Skip if table already exists or other non-critical errors
                if "already exists" not in str(e).lower():
                    logger.warning(f"SQL warning: {e}")
        
        db.commit()
        db.close()
        
        print("✅ Database tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


async def add_account(platform: str, username: str):
    """Add an account to monitor"""
    print(f"\n➕ Adding {platform}/@{username} to monitored accounts...")
    
    try:
        service = SocialAnalyticsService()
        
        # Create account record
        account_id = await service.get_or_create_account(
            platform=platform,
            username=username,
            profile_data={
                "full_name": username,
                "bio": "",
                "profile_pic_url": "",
                "is_verified": False,
                "is_business": False
            }
        )
        
        print(f"✅ Account added with ID: {account_id}")
        return account_id
        
    except Exception as e:
        print(f"❌ Error adding account: {e}")
        return None


async def fetch_initial_data(platform: str, username: str):
    """Fetch initial analytics data for an account"""
    print(f"\n📊 Fetching initial data for {platform}/@{username}...")
    
    try:
        result = await fetch_single_account(platform, username)
        
        if result.get("success"):
            print(f"\n✅ Successfully fetched and saved data!")
            print(f"   Posts saved: {result.get('posts_saved', 0)}")
            print(f"   Total views: {result.get('total_views', 0):,}")
            print(f"   Total likes: {result.get('total_likes', 0):,}")
            print(f"   Engagement: {result.get('engagement_rate', 0)}%")
            return True
        else:
            print(f"❌ Failed to fetch data: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return False


async def main():
    """Main initialization workflow"""
    print("\n" + "="*80)
    print("🚀 Social Media Analytics - System Initialization")
    print("="*80)
    
    # Initialize database connection
    print("\n🔌 Initializing database connection...")
    try:
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(database_url)
        conn = engine.connect()
        conn.close()
        print("✅ Database connected!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Step 1: Create tables
    print("\n" + "="*80)
    print("Step 1: Database Setup")
    print("="*80)
    
    if not await create_database_tables():
        print("\n❌ Database setup failed!")
        sys.exit(1)
    
    # Step 2: Add accounts
    print("\n" + "="*80)
    print("Step 2: Add Monitored Accounts")
    print("="*80)
    
    # Default accounts to monitor
    accounts_to_add = [
        ("tiktok", "isaiah_dupree"),
        # Add more accounts here
    ]
    
    print(f"\nDefault accounts to add: {len(accounts_to_add)}")
    for platform, username in accounts_to_add:
        print(f"  - {platform}/@{username}")
    
    response = input("\nAdd these accounts? (y/n): ")
    
    if response.lower() == 'y':
        for platform, username in accounts_to_add:
            await add_account(platform, username)
    
    # Ask if user wants to add more
    while True:
        add_more = input("\nAdd another account? (y/n): ")
        if add_more.lower() != 'y':
            break
        
        platform = input("Platform (tiktok/instagram/youtube): ").strip().lower()
        username = input("Username: ").strip()
        
        if platform and username:
            await add_account(platform, username)
    
    # Step 3: Fetch initial data
    print("\n" + "="*80)
    print("Step 3: Fetch Initial Data")
    print("="*80)
    
    fetch_now = input("\nFetch initial analytics data now? (y/n): ")
    
    if fetch_now.lower() == 'y':
        for platform, username in accounts_to_add:
            await fetch_initial_data(platform, username)
            await asyncio.sleep(2)  # Rate limiting
    
    # Step 4: Summary
    print("\n" + "="*80)
    print("✅ INITIALIZATION COMPLETE!")
    print("="*80)
    
    print("\n📋 Next Steps:")
    print("\n1. Set up daily cron job:")
    print("   python setup_analytics_cron.py")
    
    print("\n2. Manually fetch analytics anytime:")
    print("   python services/fetch_social_analytics.py")
    
    print("\n3. Fetch specific account:")
    print("   python services/fetch_social_analytics.py tiktok isaiah_dupree")
    
    print("\n4. View your data in the database:")
    print("   psql -d postgres -c 'SELECT * FROM latest_account_analytics;'")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
