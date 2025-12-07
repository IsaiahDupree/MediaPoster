"""
Find YouTube channel ID from handle or username
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
handle = "isaiah_dupree"  # From @isaiah_dupree

print(f"\n🔍 Looking up YouTube channel for: @{handle}\n")

# Method 1: Try search API with the handle
url = "https://www.googleapis.com/youtube/v3/search"
params = {
    "part": "snippet",
    "q": handle,
    "type": "channel",
    "maxResults": 5,
    "key": YOUTUBE_API_KEY
}

response = requests.get(url, params=params)
data = response.json()

print("Search results:")
if data.get("items"):
    for idx, item in enumerate(data["items"], 1):
        channel_id = item["id"]["channelId"]
        title = item["snippet"]["title"]
        description = item["snippet"]["description"][:100]
        
        print(f"\n{idx}. {title}")
        print(f"   Channel ID: {channel_id}")
        print(f"   Description: {description}...")
        
        # Get full channel details
        details_url = "https://www.googleapis.com/youtube/v3/channels"
        details_params = {
            "part": "snippet,statistics",
            "id": channel_id,
            "key": YOUTUBE_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("items"):
            channel = details_data["items"][0]
            stats = channel.get("statistics", {})
            custom_url = channel.get("snippet", {}).get("customUrl", "N/A")
            
            print(f"   Handle: @{custom_url}")
            print(f"   Subscribers: {int(stats.get('subscriberCount', 0)):,}")
            print(f"   Videos: {stats.get('videoCount', 0)}")
            print(f"   Views: {int(stats.get('viewCount', 0)):,}")
            
            # Check if this is the right channel
            if custom_url.lower() == handle.lower() or custom_url.lower() == f"@{handle}".lower():
                print(f"\n✅ MATCH FOUND!")
                print(f"\nAdd this to your .env file:")
                print(f"YOUTUBE_CHANNEL_ID={channel_id}")
                break
else:
    print("❌ No channels found")
    print("\nTry these alternatives:")
    print("1. Go to your YouTube channel")
    print("2. Look at the URL")
    print("3. If it shows /channel/UCxxxxx, that's your channel ID")
    print("4. If it shows /@username, go to YouTube Studio to find your channel ID")
