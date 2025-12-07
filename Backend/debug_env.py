
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print(f"Loaded DATABASE_URL: {url}")

if url:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    print(f"Modified DATABASE_URL: {url}")
else:
    print("DATABASE_URL is None")
