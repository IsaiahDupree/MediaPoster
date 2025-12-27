#!/usr/bin/env python3
"""Simple runner for passport organization"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.organize_passport_comprehensive import main

if __name__ == "__main__":
    # Set up arguments
    sys.argv = [
        'organize_passport_comprehensive.py',
        '--passport', '/Volumes/My Passport',
        '--output', 'passport_organization_docs',
        '--max-depth', '3'
    ]
    
    try:
        exit(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

