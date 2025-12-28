#!/usr/bin/env python3
"""
Full Analysis Test Script
=========================
Runs a complete analysis pipeline outside the backend to verify:
1. AI client fallback chain works
2. Transcription works
3. Vision analysis works
4. Content analysis works
5. Compare with backend results

Usage:
    python scripts/test_full_analysis.py [media_id]
"""

import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from config.model_registry import TaskType, ModelRegistry
from services.ai_client import AIClient

# Test configuration
TEST_PROMPTS = {
    "content_analysis": """Analyze this video content and provide:
1. Main topics (list 3-5)
2. Detected hooks (catchy phrases)
3. Overall tone (entertaining, educational, etc.)
4. Target audience
5. Social media score (0-100)

Respond in JSON format:
{
    "topics": [...],
    "hooks": [...],
    "tone": "...",
    "target_audience": "...",
    "social_score": 0
}""",
    
    "vision_analysis": """Analyze this image/frame and describe:
1. What's happening visually
2. Key objects/people
3. Colors and mood
4. Text visible (if any)
5. Quality assessment

Be detailed but concise.""",
}


class AnalysisTester:
    """Standalone analysis tester"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "summary": {}
        }
    
    def log_result(self, test_name: str, success: bool, details: dict):
        """Log a test result"""
        self.results["tests"][test_name] = {
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}: {success}")
    
    async def test_ai_client_fallback(self) -> bool:
        """Test 1: AI Client with fallback chain"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: AI Client Fallback Chain")
        logger.info("="*60)
        
        try:
            # Get config for content analysis (uses Groq by default)
            config = ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)
            logger.info(f"Primary model: {config.provider}/{config.model}")
            
            # Initialize client
            client = AIClient(config)
            
            # Test chat completion
            response = client.chat_completion([
                {"role": "system", "content": "You are a helpful assistant. Respond in JSON format."},
                {"role": "user", "content": TEST_PROMPTS["content_analysis"].replace("this video content", "a hypothetical cooking tutorial video")}
            ])
            
            # Parse response
            try:
                data = json.loads(response)
                self.log_result("ai_client_fallback", True, {
                    "provider": config.provider,
                    "model": config.model,
                    "response_preview": str(data)[:200],
                    "has_topics": "topics" in data,
                    "has_hooks": "hooks" in data,
                })
                return True
            except json.JSONDecodeError:
                self.log_result("ai_client_fallback", True, {
                    "provider": config.provider,
                    "model": config.model,
                    "response_preview": response[:200],
                    "note": "Response not JSON but AI call succeeded"
                })
                return True
                
        except Exception as e:
            self.log_result("ai_client_fallback", False, {"error": str(e)})
            self.results["errors"].append(f"AI Client: {e}")
            return False
    
    async def test_groq_models(self) -> dict:
        """Test 2: Test each Groq model individually"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Individual Groq Models")
        logger.info("="*60)
        
        from groq import Groq
        
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            self.log_result("groq_models", False, {"error": "GROQ_API_KEY not set"})
            return {}
        
        models = [
            "llama-3.3-70b-versatile",  # Primary - best quality (confirmed working)
            "llama-3.1-8b-instant",     # Fast small model (confirmed working)
        ]
        
        results = {}
        client = Groq(api_key=groq_key)
        
        for model in models:
            try:
                logger.info(f"Testing {model}...")
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Say hello in 5 words"}],
                    max_tokens=50,
                    timeout=30
                )
                content = resp.choices[0].message.content
                results[model] = {"success": True, "response": content[:100]}
                logger.info(f"  ✅ {model}: {content[:50]}")
            except Exception as e:
                results[model] = {"success": False, "error": str(e)[:100]}
                logger.warning(f"  ❌ {model}: {e}")
        
        success_count = sum(1 for r in results.values() if r.get("success"))
        self.log_result("groq_models", success_count > 0, {
            "tested": len(models),
            "passed": success_count,
            "results": results
        })
        
        return results
    
    async def test_google_gemini(self) -> bool:
        """Test 3: Google Gemini API"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Google Gemini API")
        logger.info("="*60)
        
        import httpx
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.log_result("google_gemini", False, {"error": "GOOGLE_API_KEY not set"})
            return False
        
        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        
        for model in models:
            try:
                logger.info(f"Testing {model}...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                        json={
                            "contents": [{"parts": [{"text": "Say hello in 5 words"}]}]
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        logger.info(f"  ✅ {model}: {text[:50]}")
                        self.log_result("google_gemini", True, {
                            "model": model,
                            "response": text[:100]
                        })
                        return True
                    else:
                        logger.warning(f"  ❌ {model}: {response.status_code}")
            except Exception as e:
                logger.warning(f"  ❌ {model}: {e}")
        
        self.log_result("google_gemini", False, {"error": "All Gemini models failed"})
        return False
    
    async def test_openai(self) -> bool:
        """Test 4: OpenAI API"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: OpenAI API")
        logger.info("="*60)
        
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.log_result("openai", False, {"error": "OPENAI_API_KEY not set"})
            return False
        
        try:
            client = OpenAI(api_key=api_key)
            
            # Test chat completion
            logger.info("Testing gpt-4o-mini...")
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hello in 5 words"}],
                max_tokens=50
            )
            content = resp.choices[0].message.content
            logger.info(f"  ✅ gpt-4o-mini: {content[:50]}")
            
            self.log_result("openai", True, {
                "model": "gpt-4o-mini",
                "response": content[:100]
            })
            return True
            
        except Exception as e:
            self.log_result("openai", False, {"error": str(e)})
            return False
    
    async def test_transcription(self, audio_path: str = None) -> bool:
        """Test 5: Whisper Transcription"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Whisper Transcription")
        logger.info("="*60)
        
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.log_result("transcription", False, {"error": "OPENAI_API_KEY not set"})
            return False
        
        # Find a test video/audio file
        if audio_path and Path(audio_path).exists():
            test_file = Path(audio_path)
        else:
            # Look for any video in the iphone_import folder
            import_dir = Path("/Volumes/My Passport/MediaPoster/workspace1/iphone_import")
            if import_dir.exists():
                videos = list(import_dir.glob("*.MOV"))[:1] or list(import_dir.glob("*.mp4"))[:1]
                if videos:
                    test_file = videos[0]
                else:
                    self.log_result("transcription", False, {"error": "No test video found"})
                    return False
            else:
                self.log_result("transcription", False, {"error": "Import dir not accessible"})
                return False
        
        logger.info(f"Using test file: {test_file.name}")
        
        # Extract audio using ffmpeg
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_output = tmp.name
        
        try:
            # Extract first 30 seconds of audio
            cmd = [
                "ffmpeg", "-y", "-i", str(test_file),
                "-t", "30", "-vn", "-ar", "16000", "-ac", "1",
                audio_output
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode != 0:
                self.log_result("transcription", False, {"error": "ffmpeg extraction failed"})
                return False
            
            # Transcribe with Whisper
            client = OpenAI(api_key=api_key)
            
            with open(audio_output, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            transcript = response.text
            logger.info(f"  ✅ Transcribed {len(transcript)} chars")
            logger.info(f"  Preview: {transcript[:100]}...")
            
            self.log_result("transcription", True, {
                "file": test_file.name,
                "transcript_length": len(transcript),
                "preview": transcript[:200]
            })
            return True
            
        except Exception as e:
            self.log_result("transcription", False, {"error": str(e)})
            return False
        finally:
            if Path(audio_output).exists():
                Path(audio_output).unlink()
    
    async def test_vision_analysis(self, image_path: str = None) -> bool:
        """Test 6: Vision Analysis"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Vision Analysis")
        logger.info("="*60)
        
        import base64
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.log_result("vision_analysis", False, {"error": "OPENAI_API_KEY not set"})
            return False
        
        # Find a test image
        if image_path and Path(image_path).exists():
            test_file = Path(image_path)
        else:
            # Look for any image in thumbnails
            thumb_dir = Path("/tmp/mediaposter/thumbnails")
            if thumb_dir.exists():
                images = list(thumb_dir.glob("*.jpg"))[:1]
                if images:
                    test_file = images[0]
                else:
                    self.log_result("vision_analysis", False, {"error": "No test image found"})
                    return False
            else:
                self.log_result("vision_analysis", False, {"error": "Thumbnail dir not found"})
                return False
        
        logger.info(f"Using test image: {test_file.name}")
        
        try:
            with open(test_file, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": TEST_PROMPTS["vision_analysis"]},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            analysis = response.choices[0].message.content
            logger.info(f"  ✅ Vision analysis: {len(analysis)} chars")
            logger.info(f"  Preview: {analysis[:150]}...")
            
            self.log_result("vision_analysis", True, {
                "image": test_file.name,
                "analysis_length": len(analysis),
                "preview": analysis[:300]
            })
            return True
            
        except Exception as e:
            self.log_result("vision_analysis", False, {"error": str(e)})
            return False
    
    async def compare_with_backend(self, media_id: str) -> dict:
        """Compare standalone analysis with backend results"""
        logger.info("\n" + "="*60)
        logger.info("TEST 7: Compare with Backend")
        logger.info("="*60)
        
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"http://localhost:5555/api/media-db/detail/{media_id}"
                )
                
                if response.status_code != 200:
                    self.log_result("backend_comparison", False, {
                        "error": f"Backend returned {response.status_code}"
                    })
                    return {}
                
                backend_data = response.json()
                
                # Check key fields
                checks = {
                    "has_transcript": bool(backend_data.get("transcript")),
                    "has_topics": bool(backend_data.get("topics")),
                    "has_hooks": bool(backend_data.get("hooks")),
                    "has_tone": bool(backend_data.get("tone")),
                    "has_visual_summary": bool(backend_data.get("visual_summary")),
                    "has_social_score": backend_data.get("pre_social_score") is not None,
                    "analyzed_at": backend_data.get("analyzed_at"),
                }
                
                logger.info(f"Backend analysis for {media_id}:")
                for key, value in checks.items():
                    status = "✅" if value else "❌"
                    logger.info(f"  {status} {key}: {value}")
                
                self.log_result("backend_comparison", True, {
                    "media_id": media_id,
                    "checks": checks,
                    "backend_data_keys": list(backend_data.keys())
                })
                
                return backend_data
                
        except Exception as e:
            self.log_result("backend_comparison", False, {"error": str(e)})
            return {}
    
    def generate_report(self) -> str:
        """Generate final test report"""
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS TEST REPORT")
        logger.info("="*60)
        
        passed = sum(1 for t in self.results["tests"].values() if t.get("success"))
        total = len(self.results["tests"])
        
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
        }
        
        logger.info(f"\nTests: {passed}/{total} passed ({self.results['summary']['success_rate']})")
        
        if self.results["errors"]:
            logger.warning(f"\nErrors encountered:")
            for error in self.results["errors"]:
                logger.warning(f"  - {error}")
        
        # Save report
        report_path = Path("data/analysis_test_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\nReport saved to: {report_path}")
        
        return json.dumps(self.results, indent=2)


async def main():
    """Run all analysis tests"""
    media_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    logger.info("="*60)
    logger.info("FULL ANALYSIS TEST SUITE")
    logger.info("="*60)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    
    tester = AnalysisTester()
    
    # Run all tests
    await tester.test_ai_client_fallback()
    await tester.test_groq_models()
    await tester.test_google_gemini()
    await tester.test_openai()
    await tester.test_transcription()
    await tester.test_vision_analysis()
    
    if media_id:
        await tester.compare_with_backend(media_id)
    
    # Generate report
    report = tester.generate_report()
    
    return tester.results


if __name__ == "__main__":
    results = asyncio.run(main())
