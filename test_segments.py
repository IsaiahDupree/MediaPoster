import requests
import json

API_URL = "http://localhost:5555/api/segments"

def test_segments():
    print("1. Listing segments...")
    response = requests.get(API_URL)
    if response.status_code != 200:
        print(f"Failed to list segments: {response.text}")
        return
    
    segments = response.json()
    print(f"Found {len(segments)} segments")
    initial_count = len(segments)

    print("\n2. Creating new segment...")
    new_segment = {
        "name": "Test Segment",
        "description": "Created by test script",
        "definition": {
            "operator": "AND",
            "conditions": [
                {"field": "activity_state", "operator": "eq", "value": "active"}
            ]
        }
    }
    
    response = requests.post(API_URL, json=new_segment)
    if response.status_code != 201:
        print(f"Failed to create segment: {response.text}")
        return
        
    created_segment = response.json()
    print(f"Created segment: {created_segment['id']}")
    segment_id = created_segment['id']

    print("\n3. Verifying list update...")
    response = requests.get(API_URL)
    segments = response.json()
    print(f"Found {len(segments)} segments")
    
    if len(segments) != initial_count + 1:
        print("ERROR: Segment count did not increase!")
    else:
        print("SUCCESS: Segment count increased.")

    print("\n4. Getting segment details...")
    response = requests.get(f"{API_URL}/{segment_id}")
    if response.status_code != 200:
        print(f"Failed to get segment details: {response.text}")
    else:
        details = response.json()
        print(f"Retrieved details for: {details['name']}")
        if details['name'] == "Test Segment":
            print("SUCCESS: Details match.")
        else:
            print("ERROR: Details do not match.")

if __name__ == "__main__":
    test_segments()
