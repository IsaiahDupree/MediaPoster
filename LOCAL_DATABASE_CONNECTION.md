# Local Supabase Database Connection Guide

## Quick Connection Details

### Database Connection String
```
postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### Connection Parameters
- **Host:** `127.0.0.1` (or `localhost`)
- **Port:** `54322`
- **Database:** `postgres`
- **Username:** `postgres`
- **Password:** `postgres`
- **Schema:** `public` (default)

### Supabase API Details
- **API URL:** `http://127.0.0.1:54321`
- **Studio URL:** `http://127.0.0.1:54323` (Web UI)
- **Publishable Key:** `sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH`
- **Secret Key:** `sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz`

---

## Connection Methods

### 1. Supabase Studio (Easiest - Web UI)

**Access:** Open in browser
```
http://127.0.0.1:54323
```

**Features:**
- Visual table editor
- SQL query editor
- View data, edit records
- Manage relationships
- No setup required

**Steps:**
1. Make sure Supabase is running: `supabase status`
2. Open `http://127.0.0.1:54323` in your browser
3. Start exploring your database!

---

### 2. Environment Variables (For Backend/Frontend)

Create a `.env` file in your `Backend/` directory:

```bash
# Database Connection
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Supabase API
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH
SUPABASE_JWT_SECRET=your-jwt-secret-here

# For async connections (SQLAlchemy)
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
```

**Python Example:**
```python
import os
from supabase import create_client

# Using Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Using direct PostgreSQL connection
import psycopg2
conn = psycopg2.connect(
    host="127.0.0.1",
    port=54322,
    database="postgres",
    user="postgres",
    password="postgres"
)
```

---

### 3. psql Command Line

**Install PostgreSQL client:**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Windows
# Download from https://www.postgresql.org/download/windows/
```

**Connect:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

**Or with individual parameters:**
```bash
psql -h 127.0.0.1 -p 54322 -U postgres -d postgres
# Password: postgres
```

**Useful psql commands:**
```sql
-- List all tables
\dt

-- Describe a table
\d table_name

-- List all databases
\l

-- Switch database
\c database_name

-- Execute SQL file
\i /path/to/file.sql

-- Exit
\q
```

---

### 4. Database GUI Clients

#### DBeaver (Free, Cross-platform)
1. Download: https://dbeaver.io/download/
2. Create new connection → PostgreSQL
3. **Connection settings:**
   - Host: `127.0.0.1`
   - Port: `54322`
   - Database: `postgres`
   - Username: `postgres`
   - Password: `postgres`
4. Test connection → Finish

#### TablePlus (macOS, Paid)
1. Download: https://tableplus.com/
2. Create new connection → PostgreSQL
3. Enter connection details (same as above)
4. Connect

#### pgAdmin (Free, Cross-platform)
1. Download: https://www.pgadmin.org/download/
2. Add new server
3. **Connection tab:**
   - Host: `127.0.0.1`
   - Port: `54322`
   - Database: `postgres`
   - Username: `postgres`
   - Password: `postgres`

#### Postico (macOS, Paid)
1. Download: https://eggerapps.at/postico/
2. New Favorite → PostgreSQL
3. Enter connection details
4. Connect

---

### 5. Python (SQLAlchemy)

**Synchronous connection:**
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

# Test connection
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print(result.fetchone())
```

**Asynchronous connection:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
)

# Use in async context
async with AsyncSession(engine) as session:
    result = await session.execute("SELECT 1")
    print(result.scalar())
```

---

### 6. Node.js / TypeScript

**Using Supabase JS Client:**
```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'http://127.0.0.1:54321',
  'sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH'
)

// Query example
const { data, error } = await supabase
  .from('videos')
  .select('*')
```

**Using pg (PostgreSQL client):**
```typescript
import { Client } from 'pg'

const client = new Client({
  host: '127.0.0.1',
  port: 54322,
  database: 'postgres',
  user: 'postgres',
  password: 'postgres',
})

await client.connect()
const result = await client.query('SELECT * FROM videos')
console.log(result.rows)
```

---

## Prerequisites

### 1. Start Local Supabase

Make sure Supabase is running:
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster
supabase status
```

If not running:
```bash
supabase start
```

### 2. Install Required Tools (Optional)

**PostgreSQL Client (for psql):**
```bash
brew install postgresql  # macOS
```

**Python packages:**
```bash
pip install psycopg2-binary  # Synchronous
pip install asyncpg          # Asynchronous
pip install supabase         # Supabase client
```

**Node.js packages:**
```bash
npm install @supabase/supabase-js
npm install pg
npm install @types/pg  # TypeScript types
```

---

## Common Connection Issues

### Issue: "Connection refused"
**Solution:** Make sure Supabase is running
```bash
supabase start
```

### Issue: "Password authentication failed"
**Solution:** Use the default password `postgres` (not your system password)

### Issue: "Database does not exist"
**Solution:** The database name is `postgres` (default)

### Issue: "Port 54322 already in use"
**Solution:** Another Supabase instance might be running. Check:
```bash
supabase stop
supabase start
```

### Issue: "SSL connection required"
**Solution:** For local development, SSL is not required. If your client insists:
- Add `?sslmode=disable` to connection string
- Or configure client to allow non-SSL connections

---

## Testing Your Connection

### Quick Test (psql)
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c "SELECT version();"
```

### Quick Test (Python)
```python
import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
conn.close()
```

### Quick Test (Supabase Studio)
1. Open http://127.0.0.1:54323
2. Go to "Table Editor"
3. You should see all your tables

---

## Useful Queries

### List all tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

### Check table structure
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'videos'
ORDER BY ordinal_position;
```

### Count rows in all tables
```sql
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY tablename;
```

### View recent migrations
```sql
SELECT * FROM supabase_migrations.schema_migrations 
ORDER BY version DESC 
LIMIT 10;
```

---

## Security Notes

⚠️ **Important:** These credentials are for **local development only**!

- Default password `postgres` is fine for local dev
- Never commit these credentials to production
- Use environment variables for sensitive data
- Local Supabase is isolated to your machine

For production, use:
- Strong, unique passwords
- Environment variables
- Connection pooling
- SSL/TLS encryption

---

## Next Steps

1. ✅ Connect using Supabase Studio (easiest)
2. ✅ Set up environment variables in your `.env` file
3. ✅ Test connection with a simple query
4. ✅ Explore your tables and data
5. ✅ Start building your application!

For more help, see:
- [Supabase Local Development Docs](https://supabase.com/docs/guides/cli/local-development)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)


