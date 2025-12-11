#!/usr/bin/env python3
"""
Database migration script for video_analysis table.
Adds missing columns that were added to the model.

Run: python scripts/migrate_video_analysis.py
"""
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def run_migration():
    """Add missing columns to video_analysis table."""
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:54322/postgres')
    engine = create_engine(db_url)
    
    print("🔄 Running video_analysis migration...")
    
    migrations = [
        ("visual_analysis", "JSONB", "Visual analysis from frame analyzer"),
        ("music_suggestion", "JSONB", "Background music recommendations"),
        ("analysis_version", "TEXT", "Version of analysis pipeline used"),
        ("key_moments", "JSONB", "Key moments detected in video"),
    ]
    
    with engine.connect() as conn:
        for column_name, column_type, description in migrations:
            try:
                sql = f"ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✅ {column_name} ({column_type}): {description}")
            except Exception as e:
                print(f"  ❌ {column_name}: {e}")
    
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    run_migration()
