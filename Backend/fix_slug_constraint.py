"""
Add unique constraint to content_items.slug
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("\n🔧 Adding unique constraint to content_items.slug...\n")

conn = engine.connect()

try:
    # Add unique constraint on content_items.slug
    try:
        conn.execute(text("""
            ALTER TABLE content_items 
            ADD CONSTRAINT content_items_slug_unique UNIQUE (slug);
        """))
        conn.commit()
        print("✅ Added unique constraint on content_items.slug")
    except Exception as e:
        conn.rollback()
        if "already exists" in str(e):
            print("ℹ️  content_items.slug constraint already exists")
        else:
            print(f"❌ Error on content_items: {e}")
            raise
    
    # Add unique constraint on content_posts (platform, external_post_id)
    try:
        conn.execute(text("""
            ALTER TABLE content_posts 
            ADD CONSTRAINT content_posts_platform_post_unique UNIQUE (platform, external_post_id);
        """))
        conn.commit()
        print("✅ Added unique constraint on content_posts(platform, external_post_id)")
    except Exception as e:
        conn.rollback()
        if "already exists" in str(e):
            print("ℹ️  content_posts constraint already exists")
        else:
            print(f"❌ Error on content_posts: {e}")
            raise
    
    print("\n✅ All constraints checked/added successfully!")
    
except Exception as e:
    print(f"❌ Fatal error: {e}")
    raise
    
finally:
    conn.close()

print("✅ Ready to run backfill!\n")
