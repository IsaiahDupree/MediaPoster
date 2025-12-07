import asyncio
import asyncpg

async def test():
    # Use direct IP with SNI for SSL
    ip = '18.213.155.45'
    conn_str = f'postgresql://postgres.zolidmgttqkmmxourdpd:Frogger12!@!@!@{ip}:5432/postgres?sslmode=require&server_settings=application_name=mediaposter'
    
    try:
        print(f"Testing direct IP: {ip}:5432...")
        conn = await asyncpg.connect(conn_str, timeout=10, server_settings={'application_name': 'mediaposter'})
        print('✓ Connection successful!')
        
        result = await conn.fetchval('SELECT 1')
        print(f'✓ Query test: {result}')
        
        await conn.close()
        print('✓ All tests passed!')
        
    except Exception as e:
        print(f'✗ Failed: {e}')

asyncio.run(test())
