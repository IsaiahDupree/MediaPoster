"""Check what tables exist in the database"""
from sqlalchemy import create_engine, text

database_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = create_engine(database_url)
conn = engine.connect()

# Get all tables
result = conn.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
"""))

tables = [row[0] for row in result]

print(f"\n📋 Found {len(tables)} tables in database:\n")
for table in tables:
    if 'social' in table.lower():
        print(f"✅ {table}")
    else:
        print(f"   {table}")

# Check specifically for social_media tables
result = conn.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    AND (table_name LIKE 'social%' OR table_name LIKE '%analytics%')
    ORDER BY table_name
"""))

social_tables = [row[0] for row in result]

print(f"\n🎯 Social media tables ({len(social_tables)}):")
for table in social_tables:
    print(f"   • {table}")

conn.close()
