import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RAPIDAPI_KEY")
HOST = os.getenv("RAPIDAPI_HOST")
BASE_URL = os.getenv("TIKTOK_CAPTCHA_API_URL")

async def check_endpoint(session, path):
    url = f"{BASE_URL}/{path}"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": HOST,
        "Content-Type": "application/json"
    }
    try:
        # Sending empty JSON to trigger 400 if endpoint exists, or 404 if not
        async with session.post(url, headers=headers, json={}) as response:
            status = response.status
            text = await response.text()
            print(f"Path '/{path}': {status}")
            if status != 404:
                print(f"  FOUND! Response: {text[:100]}...")
                return path
    except Exception as e:
        print(f"Error checking /{path}: {e}")
    return None

async def main():
    print(f"Testing endpoints on {BASE_URL}...")
    
    candidates = [
        "puzzle", "slide", "slider", 
        "whirl", "rotate", "rotation", 
        "3d", "objects", "match",
        "icon"
    ]
    
    async with aiohttp.ClientSession() as session:
        for c in candidates:
            await check_endpoint(session, c)
            await asyncio.sleep(1.5) # Wait to avoid rate limits

if __name__ == "__main__":
    asyncio.run(main())
