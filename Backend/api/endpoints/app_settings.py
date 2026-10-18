"""
Settings API endpoints for app configuration toggles.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
from loguru import logger
import os
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])

def get_engine():
    return create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres"))


class SettingUpdate(BaseModel):
    value: Any


class BulkSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


@router.get("")
async def get_all_settings():
    """Get all app settings."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT key, value, description, updated_at
            FROM app_settings
            ORDER BY key
        """))
        
        settings = {}
        for row in result:
            settings[row[0]] = {
                'value': row[1],
                'description': row[2],
                'updated_at': str(row[3]) if row[3] else None,
            }
        
        return {
            'settings': settings,
            'total': len(settings),
        }


@router.get("/{key}")
async def get_setting(key: str):
    """Get a specific setting by key."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT value, description, updated_at
            FROM app_settings
            WHERE key = :key
        """), {'key': key})
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return {
            'key': key,
            'value': row[0],
            'description': row[1],
            'updated_at': str(row[2]) if row[2] else None,
        }


@router.put("/{key}")
async def update_setting(key: str, update: SettingUpdate):
    """Update a specific setting."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if setting exists
        result = conn.execute(text("""
            SELECT key FROM app_settings WHERE key = :key
        """), {'key': key})
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        # Update the setting
        conn.execute(text("""
            UPDATE app_settings 
            SET value = :value, updated_at = NOW()
            WHERE key = :key
        """), {'key': key, 'value': json.dumps(update.value)})
        conn.commit()
        
        logger.info(f"Updated setting '{key}' to {update.value}")
        
        return {
            'key': key,
            'value': update.value,
            'success': True,
        }


@router.put("")
async def update_bulk_settings(update: BulkSettingsUpdate):
    """Update multiple settings at once."""
    engine = get_engine()
    updated = []
    
    with engine.connect() as conn:
        for key, value in update.settings.items():
            conn.execute(text("""
                UPDATE app_settings 
                SET value = :value, updated_at = NOW()
                WHERE key = :key
            """), {'key': key, 'value': json.dumps(value)})
            updated.append(key)
        
        conn.commit()
        logger.info(f"Updated {len(updated)} settings: {updated}")
        
        return {
            'updated': updated,
            'success': True,
        }


@router.post("/reset")
async def reset_settings():
    """Reset all settings to defaults."""
    engine = get_engine()
    
    defaults = [
        ('active_data_fetching', True, 'Fetch social account data after startup delay'),
        ('data_fetch_delay_minutes', 60, 'Minutes to wait before fetching data (0 = immediate)'),
        ('active_schedule_posting', True, 'Enable scheduled posting after startup delay'),
        ('posting_delay_minutes', 60, 'Minutes to wait before starting to post (0 = immediate)'),
        ('immediate_data_fetch', False, 'Skip delay and fetch data immediately on startup'),
        ('immediate_posting', False, 'Skip delay and start posting immediately on startup'),
    ]
    
    with engine.connect() as conn:
        for key, value, desc in defaults:
            conn.execute(text("""
                INSERT INTO app_settings (key, value, description, updated_at) 
                VALUES (:key, :value, :desc, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """), {'key': key, 'value': json.dumps(value), 'desc': desc})
        
        conn.commit()
        logger.info("Reset all settings to defaults")
        
        return {
            'success': True,
            'message': 'All settings reset to defaults',
        }
