"""Check existing social_accounts table structure"""
from sqlalchemy import create_engine, text, inspect

database_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = create_engine(database_url)
inspector = inspect(engine)

# Get columns for social_accounts
print("\n📊 EXISTING 'social_accounts' TABLE STRUCTURE:\n")
columns = inspector.get_columns('social_accounts')
for col in columns:
    print(f"   • {col['name']:<30} {str(col['type']):<20} {'NOT NULL' if not col['nullable'] else ''}")

# Get sample data
conn = engine.connect()
result = conn.execute(text("SELECT * FROM social_accounts LIMIT 5"))
rows = result.fetchall()

print(f"\n📋 Sample Data ({len(rows)} rows):\n")
if rows:
    for row in rows:
        print(f"   ID: {row[0]}, Name: {row[1] if len(row) > 1 else 'N/A'}")
else:
    print("   (No data yet)")

# Check for related tables
conn.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    AND table_name IN ('platform_posts', 'post_platform_publish', 'scheduled_posts')
"""))

print("\n🔗 Related existing tables:")
print("   • platform_posts")
print("   • post_platform_publish")
print("   • scheduled_posts")

conn.close()
