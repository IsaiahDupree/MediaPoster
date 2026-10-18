# How to Get Correct RapidAPI Endpoint Paths

## Current Issue

All tested endpoints return **404 Not Found**. This means we need to get the **exact endpoint paths** from the RapidAPI playground.

## Steps to Get Correct Endpoints

### 1. Open RapidAPI Playground

1. Go to: https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api
2. Make sure you're logged in
3. Click on the endpoint you want to test (e.g., "User Reels")

### 2. Test in Playground

1. In the playground, fill in the parameters:
   - `username_or_id_or_url`: `instagram`
   - `count`: `5`

2. Click **"Test Endpoint"** or **"Run"**

3. **If it works**, look at the **Request URL** shown in the playground
   - It will show something like: `POST https://instagram-scraper-stable-api.p.rapidapi.com/ENDPOINT_PATH`

### 3. Copy the Endpoint Path

The endpoint path is the part after the base URL. For example:
- If Request URL is: `POST https://instagram-scraper-stable-api.p.rapidapi.com/v1/user_reels`
- Then endpoint path is: `/v1/user_reels`

### 4. Update the Test Script

Once you have the correct endpoint path:

1. Open: `Backend/scripts/test_music_extraction_once_working.py`
2. Find the line: `ENDPOINT = "/v1/reels"`
3. Replace with the correct endpoint path you found
4. Run the script again

## Alternative: Use Code Snippets from Playground

The RapidAPI playground provides code snippets:

1. After testing an endpoint successfully
2. Click **"Code Snippets"** tab
3. Select **Python** → **httpx**
4. Copy the code
5. Extract the endpoint path from the code

Example from code snippet:
```python
response = httpx.post(
    "https://instagram-scraper-stable-api.p.rapidapi.com/v1/user_reels",  # ← This is the endpoint
    headers={...},
    json={...}
)
```

## Quick Test Script

Once you have the endpoint, test it quickly:

```python
import httpx
import os

API_KEY = os.getenv("RAPIDAPI_KEY")
ENDPOINT = "/YOUR_ENDPOINT_HERE"  # Replace with actual endpoint

async def quick_test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://instagram-scraper-stable-api.p.rapidapi.com{ENDPOINT}",
            headers={
                "X-RapidAPI-Key": API_KEY,
                "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
                "Content-Type": "application/json"
            },
            json={
                "username_or_id_or_url": "instagram",
                "count": 5
            }
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Response keys: {list(data.keys())}")
            
            # Check for music
            items = data.get("data", {}).get("items", [])
            if items and "clips_metadata" in items[0]:
                print("✓ Has clips_metadata - music extraction should work!")
        else:
            print(f"Error: {response.text}")

import asyncio
asyncio.run(quick_test())
```

## Common Issues

### Issue: "Endpoint does not exist" (404)
- **Solution:** Check that you're using the exact endpoint path from the playground
- **Solution:** Verify your API subscription has access to this endpoint

### Issue: "Unauthorized" (401)
- **Solution:** Check your `RAPIDAPI_KEY` is correct
- **Solution:** Verify the API key is active in your RapidAPI dashboard

### Issue: "Rate limit exceeded" (429)
- **Solution:** Wait a few minutes and try again
- **Solution:** Upgrade your RapidAPI plan if needed

## Next Steps

1. ✅ Get correct endpoint path from RapidAPI playground
2. ✅ Update `ENDPOINT` variable in test script
3. ✅ Run test script to verify music extraction works
4. ✅ Update documentation with working endpoints

