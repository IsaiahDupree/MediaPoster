"""
Virtual Environment Status API

Provides endpoints to check venv status and run AI/ML tasks.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.venv_manager import get_venv_manager, VenvType, transcribe_with_whisper

router = APIRouter(prefix="/api/venv", tags=["Virtual Environments"])


class TranscribeRequest(BaseModel):
    """Request model for transcription."""
    audio_path: str
    model: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = None


@router.get("/status")
async def get_venv_status():
    """
    Get status of all virtual environments.
    
    Returns which venvs are available and their configurations.
    """
    manager = get_venv_manager()
    return {
        "success": True,
        "environments": manager.get_venv_info(),
    }


@router.get("/check/{venv_type}")
async def check_venv(venv_type: str):
    """
    Check if a specific virtual environment is available.
    
    Args:
        venv_type: 'main' or 'ai_ml'
    """
    manager = get_venv_manager()
    
    try:
        venv = VenvType(venv_type) if venv_type in ["venv", "venv311"] else None
        if venv_type == "main":
            venv = VenvType.MAIN
        elif venv_type == "ai_ml":
            venv = VenvType.AI_ML
        
        if not venv:
            raise ValueError(f"Unknown venv type: {venv_type}")
            
        return {
            "success": True,
            "venv_type": venv.value,
            "available": manager.is_venv_available(venv),
            "python_path": str(manager.get_python_path(venv)),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transcribe")
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio using Whisper in the AI/ML environment.
    
    This runs Whisper in the Python 3.11 venv which has PyTorch installed.
    
    Args:
        audio_path: Path to the audio file
        model: Whisper model size (tiny, base, small, medium, large)
        language: Optional language code (e.g., "en")
    """
    import os
    
    if not os.path.exists(request.audio_path):
        raise HTTPException(status_code=400, detail=f"Audio file not found: {request.audio_path}")
    
    result = await transcribe_with_whisper(
        request.audio_path,
        model=request.model,
        language=request.language,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Transcription failed")
        )
    
    return result


@router.post("/test-ai-env")
async def test_ai_environment():
    """
    Test that the AI/ML environment is working correctly.
    
    This verifies PyTorch and Whisper are importable.
    """
    from services.venv_manager import run_in_ai_env
    
    code = '''
import json
import sys

results = {"torch": False, "whisper": False, "numpy": False}

try:
    import torch
    results["torch"] = True
    results["torch_version"] = torch.__version__
    results["cuda_available"] = torch.cuda.is_available()
except ImportError as e:
    results["torch_error"] = str(e)

try:
    import whisper
    results["whisper"] = True
except ImportError as e:
    results["whisper_error"] = str(e)

try:
    import numpy
    results["numpy"] = True
    results["numpy_version"] = numpy.__version__
except ImportError as e:
    results["numpy_error"] = str(e)

print(json.dumps(results))
'''
    
    result = await run_in_ai_env(code, timeout=60)
    
    if not result["success"]:
        return {
            "success": False,
            "error": result.get("error") or result.get("stderr"),
            "details": result,
        }
    
    try:
        import json
        output = json.loads(result["stdout"].strip())
        return {
            "success": True,
            "packages": output,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse output: {e}",
            "raw_output": result["stdout"][:500],
        }
