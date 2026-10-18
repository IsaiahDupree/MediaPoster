"""
Modal Voice Clone Deployment Script (VC-001)

Deploys IndexTTS-2 voice cloning service to Modal Labs with:
- T4 GPU (16GB memory)
- Scale to zero after 5 min idle
- Health check endpoint
- Voice cloning, embedding, and analysis endpoints

Usage:
    modal deploy scripts/modal_voice_clone.py

Environment:
    Requires Modal authentication: modal token new
"""

import io
import base64
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

# Import Modal SDK
try:
    import modal
except ImportError:
    raise ImportError(
        "Modal SDK not installed. Install with: pip install modal"
    )

# Create Modal app
app = modal.App("voice-clone-indextts2")

# Define the image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.0",
        "torchaudio==2.1.0",
        "transformers==4.36.0",
        "soundfile==0.12.1",
        "librosa==0.10.1",
        "numpy==1.26.2",
        "scipy==1.11.4",
        "pydub==0.25.1",
        "fastapi==0.108.0",
        "httpx==0.25.2",
    )
    .apt_install("ffmpeg", "libsndfile1")
)

# GPU configuration
GPU_CONFIG = modal.gpu.T4(count=1)
MEMORY_MB = 16384  # 16 GB
TIMEOUT_SECONDS = 600  # 10 minutes
SCALEDOWN_WINDOW_SECONDS = 300  # 5 minutes idle -> scale to zero


@dataclass
class VoiceCloneRequest:
    """Request for voice cloning"""
    text: str
    voice_reference_url: Optional[str] = None
    embedding_id: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    emotion: str = "neutral"
    emotion_weight: float = 0.8
    stability: float = 0.75


@dataclass
class VoiceCloneResponse:
    """Response from voice cloning"""
    audio_url: str
    duration_seconds: float
    processing_time_ms: int
    job_id: str
    status: str = "completed"
    error: Optional[str] = None


@app.cls(
    gpu=GPU_CONFIG,
    memory=MEMORY_MB,
    timeout=TIMEOUT_SECONDS,
    container_idle_timeout=SCALEDOWN_WINDOW_SECONDS,
    image=image,
    allow_concurrent_inputs=10,  # Handle multiple requests concurrently
)
class VoiceCloneService:
    """
    Voice cloning service using IndexTTS-2 model

    This service provides:
    - Voice cloning from reference audio
    - Voice embedding creation for faster generation
    - Reference audio quality analysis
    - Emotion and prosody control
    """

    def __init__(self):
        """Initialize model and load weights on container start"""
        self.model = None
        self.tokenizer = None
        self.voice_embeddings = {}  # Cache for voice embeddings

    @modal.enter()
    def load_model(self):
        """Load the IndexTTS-2 model on container startup (cold start)"""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Loading IndexTTS-2 model...")
        start_time = time.time()

        # Load from HuggingFace
        model_name = "IndexTeam/IndexTTS-2"

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )

        self.model.eval()

        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f} seconds")

    @modal.method()
    def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint

        Returns:
            Status information about the service
        """
        return {
            "status": "healthy",
            "model_loaded": self.model is not None,
            "gpu_available": self._check_gpu(),
            "timestamp": time.time(),
            "service": "voice-clone-indextts2",
            "version": "1.0.0"
        }

    @modal.method()
    def clone_voice(
        self,
        text: str,
        voice_reference_url: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        emotion: str = "neutral",
        emotion_weight: float = 0.8,
        stability: float = 0.75
    ) -> Dict[str, Any]:
        """
        Clone voice from reference audio and generate speech

        Args:
            text: Text to synthesize
            voice_reference_url: URL or base64 encoded audio
            speed: Speech speed (0.5-2.0)
            pitch: Pitch adjustment (-50 to 50)
            emotion: Emotion type (neutral, happy, sad, angry, excited)
            emotion_weight: Emotion intensity (0.0-1.0)
            stability: Voice stability (0.0-1.0)

        Returns:
            Dictionary with audio_url, duration_seconds, processing_time_ms
        """
        import torch
        import soundfile as sf
        import numpy as np

        start_time = time.time()
        job_id = self._generate_job_id()

        try:
            # Load reference audio
            reference_audio = self._load_audio(voice_reference_url)

            # Extract voice embedding
            voice_embedding = self._extract_voice_embedding(reference_audio)

            # Generate speech
            audio_output = self._synthesize_speech(
                text=text,
                voice_embedding=voice_embedding,
                speed=speed,
                pitch=pitch,
                emotion=emotion,
                emotion_weight=emotion_weight,
                stability=stability
            )

            # Calculate duration
            sample_rate = 22050
            duration_seconds = len(audio_output) / sample_rate

            # Convert to base64 for transport
            audio_base64 = self._audio_to_base64(audio_output, sample_rate)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "audio_base64": audio_base64,
                "duration_seconds": duration_seconds,
                "processing_time_ms": processing_time_ms,
                "job_id": job_id,
                "status": "completed",
                "sample_rate": sample_rate
            }

        except Exception as e:
            print(f"Error in clone_voice: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "job_id": job_id,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    @modal.method()
    def create_voice_embedding(
        self,
        voice_reference_urls: List[str],
        embedding_name: str
    ) -> Dict[str, Any]:
        """
        Create a voice embedding from reference audio(s) for faster generation

        Args:
            voice_reference_urls: List of reference audio URLs
            embedding_name: Name for this embedding

        Returns:
            Dictionary with embedding_id and metadata
        """
        import numpy as np

        start_time = time.time()

        try:
            # Load all reference audios
            reference_audios = [
                self._load_audio(url) for url in voice_reference_urls
            ]

            # Extract and average embeddings
            embeddings = [
                self._extract_voice_embedding(audio)
                for audio in reference_audios
            ]

            # Average embeddings for better quality
            averaged_embedding = np.mean(embeddings, axis=0)

            # Generate embedding ID
            embedding_id = self._generate_embedding_id(embedding_name)

            # Cache the embedding
            self.voice_embeddings[embedding_id] = averaged_embedding

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "embedding_id": embedding_id,
                "embedding_name": embedding_name,
                "num_references": len(voice_reference_urls),
                "processing_time_ms": processing_time_ms,
                "status": "completed"
            }

        except Exception as e:
            print(f"Error in create_voice_embedding: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    @modal.method()
    def generate_with_embedding(
        self,
        text: str,
        embedding_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        emotion: str = "neutral",
        emotion_weight: float = 0.8,
        stability: float = 0.75
    ) -> Dict[str, Any]:
        """
        Generate speech using a pre-created voice embedding (faster)

        Args:
            text: Text to synthesize
            embedding_id: Previously created embedding ID
            speed: Speech speed (0.5-2.0)
            pitch: Pitch adjustment (-50 to 50)
            emotion: Emotion type
            emotion_weight: Emotion intensity (0.0-1.0)
            stability: Voice stability (0.0-1.0)

        Returns:
            Dictionary with audio data
        """
        start_time = time.time()
        job_id = self._generate_job_id()

        try:
            # Retrieve cached embedding
            if embedding_id not in self.voice_embeddings:
                return {
                    "status": "failed",
                    "error": f"Embedding {embedding_id} not found",
                    "job_id": job_id
                }

            voice_embedding = self.voice_embeddings[embedding_id]

            # Generate speech
            audio_output = self._synthesize_speech(
                text=text,
                voice_embedding=voice_embedding,
                speed=speed,
                pitch=pitch,
                emotion=emotion,
                emotion_weight=emotion_weight,
                stability=stability
            )

            # Calculate duration
            sample_rate = 22050
            duration_seconds = len(audio_output) / sample_rate

            # Convert to base64
            audio_base64 = self._audio_to_base64(audio_output, sample_rate)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "audio_base64": audio_base64,
                "duration_seconds": duration_seconds,
                "processing_time_ms": processing_time_ms,
                "job_id": job_id,
                "status": "completed",
                "sample_rate": sample_rate
            }

        except Exception as e:
            print(f"Error in generate_with_embedding: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "job_id": job_id,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    @modal.method()
    def analyze_reference(self, voice_reference_url: str) -> Dict[str, Any]:
        """
        Analyze reference audio quality

        Args:
            voice_reference_url: URL or base64 encoded audio

        Returns:
            Quality metrics and recommendations
        """
        import librosa
        import numpy as np

        start_time = time.time()

        try:
            # Load audio
            audio = self._load_audio(voice_reference_url)
            sample_rate = 22050

            # Calculate quality metrics
            duration = len(audio) / sample_rate

            # RMS energy (volume)
            rms = np.sqrt(np.mean(audio**2))

            # Zero crossing rate (speech clarity indicator)
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            zcr_mean = float(np.mean(zcr))

            # Spectral centroid (brightness/clarity)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]
            spectral_centroid_mean = float(np.mean(spectral_centroid))

            # Simple quality score (0-1)
            quality_score = self._calculate_quality_score(
                duration=duration,
                rms=rms,
                zcr_mean=zcr_mean
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "status": "completed",
                "quality_score": quality_score,
                "duration_seconds": duration,
                "rms_energy": float(rms),
                "zero_crossing_rate": zcr_mean,
                "spectral_centroid": spectral_centroid_mean,
                "sample_rate": sample_rate,
                "recommendations": self._generate_recommendations(quality_score, duration),
                "processing_time_ms": processing_time_ms
            }

        except Exception as e:
            print(f"Error in analyze_reference: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    # Private helper methods

    def _load_audio(self, audio_input: str):
        """Load audio from URL or base64"""
        import soundfile as sf
        import httpx
        import numpy as np

        # Check if base64
        if audio_input.startswith("data:"):
            # Extract base64 data
            audio_data = audio_input.split(",")[1]
            audio_bytes = base64.b64decode(audio_data)
            audio, sr = sf.read(io.BytesIO(audio_bytes))
        elif audio_input.startswith("http"):
            # Download from URL
            response = httpx.get(audio_input, timeout=30.0)
            response.raise_for_status()
            audio, sr = sf.read(io.BytesIO(response.content))
        else:
            # Assume base64 without prefix
            audio_bytes = base64.b64decode(audio_input)
            audio, sr = sf.read(io.BytesIO(audio_bytes))

        # Resample to 22050 Hz if needed
        if sr != 22050:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=22050)

        return audio

    def _extract_voice_embedding(self, audio):
        """Extract voice embedding from audio"""
        import torch
        import numpy as np

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)

        # Extract embedding using model
        with torch.no_grad():
            # This is a simplified placeholder
            # In production, use actual IndexTTS-2 embedding extraction
            embedding = self.model.encode_audio(audio_tensor)

        return embedding.cpu().numpy()

    def _synthesize_speech(
        self,
        text: str,
        voice_embedding,
        speed: float,
        pitch: float,
        emotion: str,
        emotion_weight: float,
        stability: float
    ):
        """Synthesize speech from text and voice embedding"""
        import torch
        import numpy as np

        # Tokenize text
        inputs = self.tokenizer(text, return_tensors="pt")

        # Prepare generation parameters
        generation_config = {
            "voice_embedding": voice_embedding,
            "speed": speed,
            "pitch": pitch,
            "emotion": emotion,
            "emotion_weight": emotion_weight,
            "stability": stability,
            "max_length": 2048,
            "do_sample": True,
            "temperature": 0.8,
        }

        # Generate audio
        with torch.no_grad():
            # This is a simplified placeholder
            # In production, use actual IndexTTS-2 generation
            audio_output = self.model.generate(
                **inputs,
                **generation_config
            )

        # Convert to numpy
        audio_numpy = audio_output.cpu().numpy().squeeze()

        return audio_numpy

    def _audio_to_base64(self, audio, sample_rate: int) -> str:
        """Convert audio numpy array to base64"""
        import soundfile as sf

        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format='WAV')
        buffer.seek(0)
        audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        return audio_base64

    def _check_gpu(self) -> bool:
        """Check if GPU is available"""
        import torch
        return torch.cuda.is_available()

    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        import uuid
        return f"job_{uuid.uuid4().hex[:12]}"

    def _generate_embedding_id(self, name: str) -> str:
        """Generate embedding ID"""
        import hashlib
        import time

        timestamp = str(time.time())
        hash_input = f"{name}_{timestamp}"
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return f"emb_{hash_digest}"

    def _calculate_quality_score(self, duration: float, rms: float, zcr_mean: float) -> float:
        """Calculate overall quality score (0-1)"""
        # Simple heuristic scoring
        duration_score = min(duration / 30.0, 1.0)  # Ideal: 30 seconds
        volume_score = min(rms / 0.1, 1.0)  # Ideal: RMS around 0.1
        clarity_score = min(zcr_mean / 0.1, 1.0)  # Ideal: ZCR around 0.1

        # Weighted average
        quality_score = (
            0.3 * duration_score +
            0.4 * volume_score +
            0.3 * clarity_score
        )

        return float(quality_score)

    def _generate_recommendations(self, quality_score: float, duration: float) -> List[str]:
        """Generate recommendations based on quality analysis"""
        recommendations = []

        if quality_score < 0.5:
            recommendations.append("Quality score is low. Consider using higher quality audio.")

        if duration < 10:
            recommendations.append("Audio is too short. Use 10-30 seconds for best results.")
        elif duration > 60:
            recommendations.append("Audio is too long. Consider trimming to 10-30 seconds.")

        if not recommendations:
            recommendations.append("Audio quality is good.")

        return recommendations


# Web endpoint for API access
@app.function(
    image=image,
    allow_concurrent_inputs=100,
)
@modal.web_endpoint(method="POST", label="clone-voice")
def api_clone_voice(request: Dict[str, Any]):
    """
    Public API endpoint for voice cloning

    Request:
        {
            "text": "Text to synthesize",
            "voice_reference_url": "https://...",
            "speed": 1.0,
            "pitch": 0.0,
            "emotion": "neutral",
            "emotion_weight": 0.8,
            "stability": 0.75
        }
    """
    service = VoiceCloneService()

    text = request.get("text")
    voice_reference_url = request.get("voice_reference_url")
    speed = request.get("speed", 1.0)
    pitch = request.get("pitch", 0.0)
    emotion = request.get("emotion", "neutral")
    emotion_weight = request.get("emotion_weight", 0.8)
    stability = request.get("stability", 0.75)

    result = service.clone_voice.remote(
        text=text,
        voice_reference_url=voice_reference_url,
        speed=speed,
        pitch=pitch,
        emotion=emotion,
        emotion_weight=emotion_weight,
        stability=stability
    )

    return result


@app.function(image=image)
@modal.web_endpoint(method="GET", label="health")
def api_health():
    """Health check endpoint"""
    service = VoiceCloneService()
    return service.health_check.remote()


# Local entrypoint for testing
@app.local_entrypoint()
def main():
    """
    Test the voice cloning service locally
    """
    print("Testing Voice Clone Service...")

    # Test health check
    service = VoiceCloneService()
    health = service.health_check.remote()
    print(f"Health check: {health}")

    # Test with sample text (requires actual reference audio in production)
    # result = service.clone_voice.remote(
    #     text="Hello, this is a test of the voice cloning system.",
    #     voice_reference_url="https://example.com/reference.wav"
    # )
    # print(f"Clone result: {result}")


if __name__ == "__main__":
    # This allows running: python scripts/modal_voice_clone.py
    print(__doc__)
    print("\nTo deploy:")
    print("  modal deploy scripts/modal_voice_clone.py")
    print("\nTo test:")
    print("  modal run scripts/modal_voice_clone.py")
