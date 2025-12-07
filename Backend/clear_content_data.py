"""
Clear existing content data to prepare for improved backfill
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("\n🧹 Clearing existing content data...\n")

conn = engine.connect()

try:
    # Delete in correct order due to foreign keys
    print("Deleting follower engagement scores...")
    conn.execute(text("DELETE FROM follower_engagement_scores"))
    
    print("Deleting follower interactions...")
    conn.execute(text("DELETE FROM follower_interactions"))
    
    print("Deleting followers...")
    conn.execute(text("DELETE FROM followers"))
    
    print("Deleting content tags...")
    conn.execute(text("DELETE FROM content_tags"))
    
    print("Deleting content posts...")
    conn.execute(text("DELETE FROM content_posts"))
    
    print("Deleting content items...")
    conn.execute(text("DELETE FROM content_items"))
    
    conn.commit()
    
    print("\n✅ All content data cleared!")
    print("Ready to run backfill with improved titles.\n")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Error: {e}\n")
    raise

finally:
    conn.close()
