import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("Backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

async def inspect_table():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        try:
            # Try to select one row to see columns
            result = await conn.execute(text("SELECT * FROM segments LIMIT 1"))
            print("Columns:", result.keys())
        except Exception as e:
            print("Error:", e)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_table())
