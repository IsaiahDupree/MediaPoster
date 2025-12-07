import asyncio
import psycopg

async def test():
    conn_str = 'postgresql://postgres.zolidmgttqkmmxourdpd:Frogger12!@!@!@aws-1-us-east-1.pooler.supabase.com:5432/postgres'
    
    try:
        print("Testing with psycopg (async)...")
        print("Host: aws-1-us-east-1.pooler.supabase.com:5432")
        print()
        
        async with await psycopg.AsyncConnection.connect(conn_str, connect_timeout=10) as conn:
            print('✓ Connection successful!')
            
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1')
                result = await cur.fetchone()
                print(f'✓ Query test: SELECT 1 = {result[0]}')
            
        print('✓ All tests passed! psycopg works!')
        
    except Exception as e:
        print(f'✗ Connection failed: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
