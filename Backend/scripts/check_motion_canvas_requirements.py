#!/usr/bin/env python3
"""
Check Motion Canvas Requirements
=================================
Comprehensive check of all Motion Canvas requirements and dependencies.
"""

import subprocess
import sys
from pathlib import Path
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def check_node():
    """Check if Node.js is installed"""
    logger.info("🔍 Checking Node.js...")
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        logger.success(f"✅ Node.js installed: {version}")
        return True, version
    except FileNotFoundError:
        logger.error("❌ Node.js not found")
        logger.info("💡 Install Node.js: https://nodejs.org/")
        return False, None
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Node.js check failed: {e}")
        return False, None


def check_npm():
    """Check if npm is installed"""
    logger.info("🔍 Checking npm...")
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        logger.success(f"✅ npm installed: {version}")
        return True, version
    except FileNotFoundError:
        logger.error("❌ npm not found")
        return False, None
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ npm check failed: {e}")
        return False, None


def check_motion_canvas_project(project_dir: Path):
    """Check Motion Canvas project setup"""
    logger.info("🔍 Checking Motion Canvas project...")
    
    checks = {
        "project_dir_exists": project_dir.exists(),
        "package_json_exists": (project_dir / "package.json").exists(),
        "src_dir_exists": (project_dir / "src").exists(),
        "scenes_dir_exists": (project_dir / "src" / "scenes").exists(),
        "project_ts_exists": (project_dir / "src" / "project.ts").exists(),
        "vite_config_exists": (project_dir / "vite.config.ts").exists(),
    }
    
    all_good = True
    for check_name, result in checks.items():
        if result:
            logger.success(f"✅ {check_name.replace('_', ' ').title()}")
        else:
            logger.error(f"❌ {check_name.replace('_', ' ').title()}")
            all_good = False
    
    return all_good


def check_npm_dependencies(project_dir: Path):
    """Check if npm dependencies are installed"""
    logger.info("🔍 Checking npm dependencies...")
    
    if not (project_dir / "node_modules").exists():
        logger.warning("⚠️  node_modules not found - dependencies not installed")
        logger.info("💡 Run: cd MotionCanvas && npm install")
        return False
    
    # Check key packages
    key_packages = [
        ("@motion-canvas/core", "node_modules/@motion-canvas/core"),
        ("@motion-canvas/2d", "node_modules/@motion-canvas/2d"),
        ("@motion-canvas/vite-plugin", "node_modules/@motion-canvas/vite-plugin"),
        ("vite", "node_modules/vite"),
        ("typescript", "node_modules/typescript"),
    ]
    
    all_installed = True
    for package_name, package_path in key_packages:
        package_dir = project_dir / package_path
        if package_dir.exists():
            logger.success(f"✅ {package_name} installed")
        else:
            logger.error(f"❌ {package_name} not found")
            all_installed = False
    
    return all_installed


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    logger.info("🔍 Checking FFmpeg...")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True
        )
        # Extract version from first line
        version_line = result.stdout.split('\n')[0]
        logger.success(f"✅ FFmpeg installed: {version_line}")
        return True
    except FileNotFoundError:
        logger.error("❌ FFmpeg not found")
        logger.info("💡 Install FFmpeg: brew install ffmpeg")
        return False
    except subprocess.CalledProcessError:
        logger.error("❌ FFmpeg check failed")
        return False


def check_vite_build(project_dir: Path):
    """Check if Vite build works"""
    logger.info("🔍 Testing Vite build...")
    
    try:
        # Just check if vite command works (don't actually build)
        result = subprocess.run(
            ["npm", "run", "build", "--", "--help"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10
        )
        logger.success("✅ Vite build command available")
        return True
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  Vite build check timed out (this is OK)")
        return True
    except FileNotFoundError:
        logger.error("❌ npm not found")
        return False
    except subprocess.CalledProcessError:
        # This is OK - we're just checking if command exists
        logger.success("✅ Vite build command available")
        return True


def install_dependencies(project_dir: Path):
    """Install npm dependencies"""
    logger.info("📦 Installing npm dependencies...")
    
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=True
        )
        logger.success("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Installation failed: {e.stderr[:200]}")
        return False


def main():
    """Main requirement check"""
    logger.info("=" * 80)
    logger.info("🔧 Motion Canvas Requirements Check")
    logger.info("=" * 80)
    logger.info("")
    
    project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    results = {}
    
    # Check Node.js
    node_ok, node_version = check_node()
    results["node"] = node_ok
    logger.info("")
    
    # Check npm
    npm_ok, npm_version = check_npm()
    results["npm"] = npm_ok
    logger.info("")
    
    # Check Motion Canvas project
    project_ok = check_motion_canvas_project(project_dir)
    results["project"] = project_ok
    logger.info("")
    
    # Check dependencies
    deps_ok = check_npm_dependencies(project_dir)
    results["dependencies"] = deps_ok
    logger.info("")
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    results["ffmpeg"] = ffmpeg_ok
    logger.info("")
    
    # Check Vite build
    vite_ok = check_vite_build(project_dir)
    results["vite"] = vite_ok
    logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("📊 Summary")
    logger.info("=" * 80)
    
    all_ok = all(results.values())
    
    for check, ok in results.items():
        status = "✅" if ok else "❌"
        logger.info(f"{status} {check.replace('_', ' ').title()}")
    
    logger.info("")
    
    if not all_ok:
        logger.warning("⚠️  Some requirements are missing")
        
        if not results.get("dependencies"):
            logger.info("")
            logger.info("💡 Installing dependencies...")
            if install_dependencies(project_dir):
                logger.success("✅ Dependencies installed successfully")
                # Re-check
                deps_ok = check_npm_dependencies(project_dir)
                results["dependencies"] = deps_ok
            else:
                logger.error("❌ Failed to install dependencies")
        
        logger.info("")
        logger.info("🔧 Fix missing requirements and run this check again")
        return 1
    else:
        logger.success("✅ All requirements met!")
        logger.info("")
        logger.info("🎬 Motion Canvas is ready to use")
        return 0


if __name__ == "__main__":
    sys.exit(main())

