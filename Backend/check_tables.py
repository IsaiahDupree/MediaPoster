"""Check if Content Ops tables exist in the database"""
from sqlalchemy import create_engine, text

database_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = create_engine(database_url)
conn = engine.connect()

# Check for Content Ops tables
content_ops_tables = ['brands', 'offers', 'icps', 'content_templates', 'touchpoints']
result = conn.execute(text("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('brands', 'offers', 'icps', 'content_templates', 'touchpoints')
    ORDER BY table_name
"""))

found_tables = [row[0] for row in result]

print(f"\n📋 Content Ops Tables Status:\n")
for table in content_ops_tables:
    if table in found_tables:
        print(f"✅ {table}")
    else:
        print(f"❌ {table} - NOT FOUND")

if len(found_tables) == len(content_ops_tables):
    print("\n✅ All Content Ops tables exist!")
else:
    print(f"\n⚠️ {len(content_ops_tables) - len(found_tables)} tables missing. Migration may have failed.")

conn.close()
