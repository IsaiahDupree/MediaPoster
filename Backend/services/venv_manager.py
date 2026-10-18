"""
Virtual Environment Manager

Manages multiple Python virtual environments for different workloads:
- venv (Python 3.14): Main application, FastAPI, general tasks
- venv311 (Python 3.11): AI/ML tasks requiring PyTorch, Whisper, etc.

This allows the main app to stay on the latest Python while still
supporting ML libraries that require older Python versions.
"""
import os
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger
from enum import Enum
import tempfile


class VenvType(Enum):
    """Available virtual environment types."""
    MAIN = "venv"           # Python 3.14 - Main app
    AI_ML = "venv311"       # Python 3.11 - AI/ML tasks (Whisper, PyTorch)


# Base directory for venvs
BACKEND_DIR = Path(__file__).parent.parent
VENV_CONFIGS = {
    VenvType.MAIN: {
        "path": BACKEND_DIR / "venv",
        "python_version": "3.14",
        "description": "Main application environment",
        "packages": ["fastapi", "uvicorn", "pydantic", "openai"],
    },
    VenvType.AI_ML: {
        "path": BACKEND_DIR / "venv311",
        "python_version": "3.11",
        "description": "AI/ML environment (Whisper, PyTorch)",
        "packages": ["torch", "whisper", "numpy", "torchaudio"],
    },
}


class VenvManager:
    """
    Manages execution of Python code in different virtual environments.
    
    Usage:
        manager = VenvManager()
        
        # Run a script in the AI/ML environment
        result = await manager.run_script(
            VenvType.AI_ML,
            "transcribe.py",
            args=["--audio", "/path/to/audio.mp3"]
        )
        
        # Execute Python code directly
        result = await manager.execute_code(
            VenvType.AI_ML,
            '''
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe("/path/to/audio.mp3")
            print(json.dumps(result))
            '''
        )
    """
    
    def __init__(self):
        self.backend_dir = BACKEND_DIR
        self._verify_venvs()
    
    def _verify_venvs(self):
        """Verify that required virtual environments exist."""
        for venv_type, config in VENV_CONFIGS.items():
            venv_path = config["path"]
            python_path = venv_path / "bin" / "python"
            
            if not python_path.exists():
                logger.warning(
                    f"Virtual environment {venv_type.value} not found at {venv_path}. "
                    f"Some features may not work."
                )
            else:
                logger.debug(f"Found venv {venv_type.value} at {venv_path}")
    
    def get_python_path(self, venv_type: VenvType) -> Path:
        """Get the Python executable path for a virtual environment."""
        return VENV_CONFIGS[venv_type]["path"] / "bin" / "python"
    
    def is_venv_available(self, venv_type: VenvType) -> bool:
        """Check if a virtual environment is available."""
        return self.get_python_path(venv_type).exists()
    
    async def run_script(
        self,
        venv_type: VenvType,
        script_path: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Run a Python script in the specified virtual environment.
        
        Args:
            venv_type: Which venv to use
            script_path: Path to the Python script
            args: Command line arguments
            cwd: Working directory
            timeout: Timeout in seconds
            env: Additional environment variables
            
        Returns:
            Dict with stdout, stderr, return_code, and success
        """
        python_path = self.get_python_path(venv_type)
        
        if not python_path.exists():
            return {
                "success": False,
                "error": f"Virtual environment {venv_type.value} not available",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }
        
        cmd = [str(python_path), script_path]
        if args:
            cmd.extend(args)
        
        # Merge environment variables
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        try:
            logger.debug(f"Running in {venv_type.value}: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or str(self.backend_dir),
                env=process_env,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "return_code": process.returncode,
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Script timed out after {timeout}s: {script_path}")
            return {
                "success": False,
                "error": f"Script timed out after {timeout} seconds",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }
        except Exception as e:
            logger.exception(f"Error running script: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }
    
    async def execute_code(
        self,
        venv_type: VenvType,
        code: str,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code directly in the specified virtual environment.
        
        Args:
            venv_type: Which venv to use
            code: Python code to execute
            timeout: Timeout in seconds
            env: Additional environment variables
            
        Returns:
            Dict with stdout, stderr, return_code, and success
        """
        python_path = self.get_python_path(venv_type)
        
        if not python_path.exists():
            return {
                "success": False,
                "error": f"Virtual environment {venv_type.value} not available",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }
        
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_script = f.name
        
        try:
            result = await self.run_script(
                venv_type,
                temp_script,
                timeout=timeout,
                env=env,
            )
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_script)
            except Exception:
                pass
    
    async def transcribe_audio(
        self,
        audio_path: str,
        model: str = "base",
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper in the AI/ML environment.
        
        Args:
            audio_path: Path to audio file
            model: Whisper model size (tiny, base, small, medium, large)
            language: Optional language code (e.g., "en", "es")
            
        Returns:
            Dict with transcription text and segments
        """
        lang_arg = f', language="{language}"' if language else ""
        
        code = f'''
import whisper
import json
import sys

try:
    model = whisper.load_model("{model}")
    result = model.transcribe("{audio_path}"{lang_arg})
    
    output = {{
        "text": result["text"],
        "segments": [
            {{
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
            }}
            for s in result.get("segments", [])
        ],
        "language": result.get("language", "unknown"),
    }}
    print(json.dumps(output))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.exit(1)
'''
        
        result = await self.execute_code(
            VenvType.AI_ML,
            code,
            timeout=600,  # Transcription can take a while
        )
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error") or result.get("stderr", "Unknown error"),
            }
        
        try:
            output = json.loads(result["stdout"].strip())
            if "error" in output:
                return {"success": False, "error": output["error"]}
            return {"success": True, **output}
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": f"Failed to parse output: {result['stdout'][:200]}",
            }
    
    def get_venv_info(self) -> Dict[str, Any]:
        """Get information about all virtual environments."""
        info = {}
        for venv_type, config in VENV_CONFIGS.items():
            python_path = self.get_python_path(venv_type)
            info[venv_type.value] = {
                "available": python_path.exists(),
                "path": str(config["path"]),
                "python_version": config["python_version"],
                "description": config["description"],
                "packages": config["packages"],
            }
        return info


# Global singleton instance
_manager: Optional[VenvManager] = None


def get_venv_manager() -> VenvManager:
    """Get the global VenvManager instance."""
    global _manager
    if _manager is None:
        _manager = VenvManager()
    return _manager


# Convenience functions for common operations
async def transcribe_with_whisper(
    audio_path: str,
    model: str = "base",
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to transcribe audio with Whisper.
    
    Args:
        audio_path: Path to audio file
        model: Whisper model (tiny, base, small, medium, large)
        language: Optional language code
        
    Returns:
        Dict with transcription results
    """
    manager = get_venv_manager()
    return await manager.transcribe_audio(audio_path, model, language)


async def run_in_ai_env(code: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Run Python code in the AI/ML environment (Python 3.11 with PyTorch).
    
    Args:
        code: Python code to execute
        timeout: Timeout in seconds
        
    Returns:
        Execution result
    """
    manager = get_venv_manager()
    return await manager.execute_code(VenvType.AI_ML, code, timeout)
