import asyncio
import asyncpg

async def test():
    # URL-encoded password
    conn_str = 'postgresql://postgres.zolidmgttqkmmxourdpd:Frogger12%21%40%21%40%21@aws-1-us-east-1.pooler.supabase.com:5432/postgres'
    
    try:
        print("Testing with URL-encoded password...")
        print("Host: aws-1-us-east-1.pooler.supabase.com:5432")
        print()
        
        conn = await asyncpg.connect(conn_str, timeout=10)
        print('✓ Connection successful!')
        
        result = await conn.fetchval('SELECT 1')
        print(f'✓ Query test: SELECT 1 = {result}')
        
        # Test actual query
        version = await conn.fetchval('SELECT version()')
        print(f'✓ PostgreSQL version: {version[:50]}...')
        
        await conn.close()
        print('\n✓ ALL TESTS PASSED! Supabase connection works!')
        
    except Exception as e:
        print(f'✗ Connection failed: {type(e).__name__}: {e}')

if __name__ == '__main__':
    asyncio.run(test())
