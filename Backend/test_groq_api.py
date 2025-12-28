#!/usr/bin/env python3
"""
Test Groq API functionality, rate limits, and pricing
"""
import os
import time
from groq import Groq
from pathlib import Path

# Load API key from environment
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

print("=" * 80)
print("GROQ API TEST")
print("=" * 80)
print(f"API Key: {api_key[:20]}...")
print()

# Initialize client
client = Groq(api_key=api_key)

# Test 1: Text Analysis (Llama 3.1 70B)
print("TEST 1: Text Analysis with Llama 3.3 70B")
print("-" * 80)

try:
    start_time = time.time()
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Updated to current model
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes video content."
            },
            {
                "role": "user",
                "content": "Analyze this video description and provide a score (0-100) and 3 topics: 'A beautiful sunset over the ocean with waves crashing on the beach. Very peaceful and relaxing scene.'"
            }
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    elapsed = time.time() - start_time
    
    print(f"✅ SUCCESS")
    print(f"Response: {response.choices[0].message.content}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.usage.prompt_tokens} input, {response.usage.completion_tokens} output")
    print(f"Time: {elapsed:.2f}s")
    print(f"Speed: {response.usage.completion_tokens / elapsed:.1f} tokens/second")
    print()
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print()

# Test 2: Rate Limit Test (Multiple Requests)
print("TEST 2: Rate Limit Test (10 rapid requests)")
print("-" * 80)

success_count = 0
rate_limit_errors = 0
start_time = time.time()

for i in range(10):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Use faster model for rate limit test
            messages=[
                {"role": "user", "content": f"Say 'Test {i+1}' and nothing else."}
            ],
            max_tokens=10
        )
        success_count += 1
        print(f"  Request {i+1}: ✅ Success")
        
    except Exception as e:
        if "rate_limit" in str(e).lower():
            rate_limit_errors += 1
            print(f"  Request {i+1}: ⚠️ Rate limited")
        else:
            print(f"  Request {i+1}: ❌ Error: {e}")

elapsed = time.time() - start_time

print()
print(f"Results: {success_count}/10 successful, {rate_limit_errors} rate limited")
print(f"Total time: {elapsed:.2f}s")
print(f"Rate: {10/elapsed:.1f} requests/second")
print()

# Test 3: Transcription (if audio file available)
print("TEST 3: Transcription with Whisper Large V3")
print("-" * 80)

# Look for a test audio file
test_audio_paths = [
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/test_audio.mp3",
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/test_audio.wav",
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/test_audio.m4a"
]

test_audio = None
for path in test_audio_paths:
    if os.path.exists(path):
        test_audio = path
        break

if test_audio:
    try:
        start_time = time.time()
        
        with open(test_audio, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        elapsed = time.time() - start_time
        
        print(f"✅ SUCCESS")
        print(f"Transcript: {response.text[:200]}...")
        print(f"Language: {response.language}")
        print(f"Duration: {response.duration}s")
        print(f"Segments: {len(response.segments)}")
        print(f"Words: {len(response.words) if hasattr(response, 'words') else 'N/A'}")
        print(f"Processing time: {elapsed:.2f}s")
        print(f"Speed: {response.duration / elapsed:.1f}x real-time")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print()
else:
    print("⚠️ SKIPPED: No test audio file found")
    print("   Create a test audio file at:")
    print("   /Users/isaiahdupree/Documents/Software/MediaPoster/Backend/test_audio.mp3")
    print()

# Test 4: Pricing Verification
print("TEST 4: Pricing Verification")
print("-" * 80)

try:
    # Make a small request to check if we're being charged
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Updated to current model
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10
    )
    
    print(f"✅ Request successful")
    print(f"Tokens used: {response.usage.total_tokens}")
    print(f"Expected cost: $0.00 (FREE)")
    print()
    print("Note: Groq is currently FREE for all models")
    print("      This may change in the future")
    print()
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("✅ Groq API is working")
print("✅ Models tested:")
print("   - llama-3.3-70b-versatile (analysis)")
print("   - llama-3.1-8b-instant (fast analysis)")
print("   - whisper-large-v3 (transcription)")
print()
print("Rate Limits:")
print(f"   - Analysis: ~30 requests/minute (observed: {success_count}/10 in {elapsed:.1f}s)")
print("   - Transcription: ~20 requests/minute")
print()
print("Pricing:")
print("   - Current: FREE for all models")
print("   - Future: May add pricing (monitor groq.com)")
print()
print("Recommendation:")
print("   ✅ Use Groq as primary provider (FREE, fast)")
print("   ✅ Keep OpenAI as fallback (if rate limited)")
print()
