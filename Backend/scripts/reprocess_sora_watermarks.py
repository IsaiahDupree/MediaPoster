#!/usr/bin/env python3
"""
Reprocess Sora videos to remove watermarks by cropping bottom 100px.
"""

import subprocess
from pathlib import Path
from datetime import datetime

SORA_DIR = Path('/Users/isaiahdupree/Documents/SoraVideos')

def log(msg):
    """Print with timestamp."""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}")

def main():
    log("="*60)
    log("SORA WATERMARK REMOVAL - CROP METHOD")
    log("="*60)
    
    # Get all watermarked videos
    watermarked = sorted(SORA_DIR.glob('*_watermarked.mp4'))
    log(f"Found {len(watermarked)} watermarked videos to reprocess")
    
    reprocessed = 0
    failed = 0
    
    for i, wm in enumerate(watermarked, 1):
        video_id = wm.stem.replace('_watermarked', '')
        clean = SORA_DIR / f'{video_id}.mp4'
        
        log(f"[{i}/{len(watermarked)}] Processing: {video_id[:20]}...")
        
        # Delete old clean version
        if clean.exists():
            clean.unlink()
            log(f"  Deleted old clean version")
        
        # Get dimensions
        probe = subprocess.run([
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            str(wm)
        ], capture_output=True, text=True)
        
        try:
            width, height = map(int, probe.stdout.strip().split(','))
            crop_height = height - 100
            log(f"  Dimensions: {width}x{height} -> {width}x{crop_height}")
        except:
            log(f"  ERROR: Could not get dimensions")
            failed += 1
            continue
        
        # Crop to remove watermark
        cmd = [
            'ffmpeg', '-y', '-i', str(wm),
            '-vf', f'crop={width}:{crop_height}:0:0',
            '-c:a', 'copy',
            str(clean)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            reprocessed += 1
            size_mb = clean.stat().st_size / (1024*1024)
            log(f"  ✓ Done ({size_mb:.1f} MB)")
        else:
            failed += 1
            log(f"  ✗ FAILED: {result.stderr[:100]}")
    
    log("")
    log("="*60)
    log("COMPLETE")
    log("="*60)
    log(f"✓ Reprocessed: {reprocessed}")
    log(f"✗ Failed: {failed}")
    log(f"📁 Output: {SORA_DIR}")

if __name__ == "__main__":
    main()
