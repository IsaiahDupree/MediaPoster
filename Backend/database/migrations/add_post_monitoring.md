"""
Database migration: Add post monitoring tables
Run: alembic revision --autogenerate -m "add post monitoring tables"
"""

# This file documents the schema changes - actual migration will be via Alembic

# Tables to create:
# 1. post_submissions - Track all Blotato submissions
# 2. post_analytics - Store analytics snapshots at intervals  
# 3. post_comments - Individual comments for sentiment analysis

# See database/models/monitoring.py for full schema
