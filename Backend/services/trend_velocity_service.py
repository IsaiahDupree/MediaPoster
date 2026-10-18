"""
Trend Velocity Service
Tracks and calculates velocity (acceleration) for trending content.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine, text


class TrendVelocity(BaseModel):
    """Velocity score for a trend"""
    trend_type: str  # hashtag, sound, keyword
    trend_id: str
    trend_name: str
    current_count: int
    velocity_1d: float = 0.0
    velocity_7d: float = 0.0
    velocity_30d: float = 0.0
    acceleration: float = 0.0
    trending_score: float = 0.0
    last_updated: datetime = None
    metadata: Dict[str, Any] = {}  # Additional metadata (e.g., artist for sounds)


class TrendVelocityService:
    """
    Service for tracking and calculating trend velocity.
    
    Velocity = rate of change in usage/engagement
    Acceleration = rate of change of velocity (trends speeding up)
    
    Formula:
    - velocity_Xd = (current - X_days_ago) / X_days_ago * 100
    - acceleration = velocity_1d - velocity_7d (positive = accelerating)
    - trending_score = current_count * (1 + velocity_7d/100) * (1 + acceleration/100)
    """
    
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(self.database_url)
    
    def record_hashtag_snapshot(self, hashtag: str, media_count: int):
        """Record a snapshot of hashtag usage"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO trend_hashtag_snapshots (hashtag, media_count, snapshot_at)
                VALUES (:hashtag, :media_count, NOW())
                ON CONFLICT (hashtag, snapshot_at) DO UPDATE
                SET media_count = :media_count
            """), {"hashtag": hashtag, "media_count": media_count})
            conn.commit()
    
    def record_sound_snapshot(
        self, 
        audio_id: str, 
        usage_count: int,
        title: str = None,
        artist: str = None
    ):
        """Record a snapshot of sound usage"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO trend_sound_snapshots (audio_id, title, artist, usage_count, snapshot_at)
                VALUES (:audio_id, :title, :artist, :usage_count, NOW())
                ON CONFLICT (audio_id, snapshot_at) DO UPDATE
                SET usage_count = :usage_count, title = :title, artist = :artist
            """), {
                "audio_id": audio_id, 
                "title": title,
                "artist": artist,
                "usage_count": usage_count
            })
            conn.commit()
    
    def record_keyword_snapshot(
        self,
        keyword: str,
        keyword_type: str,
        frequency: int,
        avg_engagement: float = 0
    ):
        """Record a snapshot of keyword frequency"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO trend_keyword_snapshots 
                (keyword, keyword_type, frequency, avg_engagement, snapshot_at)
                VALUES (:keyword, :keyword_type, :frequency, :avg_engagement, NOW())
                ON CONFLICT (keyword, keyword_type, snapshot_at) DO UPDATE
                SET frequency = :frequency, avg_engagement = :avg_engagement
            """), {
                "keyword": keyword,
                "keyword_type": keyword_type,
                "frequency": frequency,
                "avg_engagement": avg_engagement
            })
            conn.commit()
    
    def calculate_velocity(
        self, 
        trend_type: str, 
        trend_id: str,
        hours: int = 24
    ) -> float:
        """Calculate velocity for a trend over specified hours"""
        table_map = {
            "hashtag": ("trend_hashtag_snapshots", "hashtag", "media_count"),
            "sound": ("trend_sound_snapshots", "audio_id", "usage_count"),
            "keyword": ("trend_keyword_snapshots", "keyword", "frequency")
        }
        
        if trend_type not in table_map:
            return 0.0
        
        table, id_col, count_col = table_map[trend_type]
        
        with self.engine.connect() as conn:
            # Get current count
            current = conn.execute(text(f"""
                SELECT {count_col} FROM {table}
                WHERE {id_col} = :trend_id
                ORDER BY snapshot_at DESC LIMIT 1
            """), {"trend_id": trend_id}).scalar()
            
            # Get previous count
            previous = conn.execute(text(f"""
                SELECT {count_col} FROM {table}
                WHERE {id_col} = :trend_id
                AND snapshot_at <= NOW() - INTERVAL '{hours} hours'
                ORDER BY snapshot_at DESC LIMIT 1
            """), {"trend_id": trend_id}).scalar()
        
        if not current or not previous or previous == 0:
            return 0.0
        
        return ((current - previous) / previous) * 100
    
    def update_velocity_scores(self, trend_type: str = None):
        """Update velocity scores for all trends of a type"""
        types_to_update = [trend_type] if trend_type else ["hashtag", "sound", "keyword"]
        
        for t_type in types_to_update:
            if t_type == "hashtag":
                self._update_hashtag_velocities()
            elif t_type == "sound":
                self._update_sound_velocities()
            elif t_type == "keyword":
                self._update_keyword_velocities()
    
    def _update_hashtag_velocities(self):
        """Update velocity scores for hashtags"""
        with self.engine.connect() as conn:
            # Get distinct hashtags with recent snapshots
            hashtags = conn.execute(text("""
                SELECT DISTINCT hashtag, 
                       (SELECT media_count FROM trend_hashtag_snapshots s2 
                        WHERE s2.hashtag = s.hashtag 
                        ORDER BY snapshot_at DESC LIMIT 1) as current_count
                FROM trend_hashtag_snapshots s
                WHERE snapshot_at > NOW() - INTERVAL '7 days'
            """)).fetchall()
            
            for row in hashtags:
                hashtag, current_count = row
                v1d = self.calculate_velocity("hashtag", hashtag, 24)
                v7d = self.calculate_velocity("hashtag", hashtag, 168)
                v30d = self.calculate_velocity("hashtag", hashtag, 720)
                
                acceleration = v1d - v7d
                trending_score = current_count * (1 + v7d/100) * (1 + max(0, acceleration)/100)
                
                conn.execute(text("""
                    INSERT INTO trend_velocity_scores 
                    (trend_type, trend_id, trend_name, current_count, 
                     velocity_1d, velocity_7d, velocity_30d, acceleration, trending_score, last_updated)
                    VALUES ('hashtag', :id, :name, :count, :v1d, :v7d, :v30d, :acc, :score, NOW())
                    ON CONFLICT (trend_type, trend_id) DO UPDATE
                    SET current_count = :count, velocity_1d = :v1d, velocity_7d = :v7d,
                        velocity_30d = :v30d, acceleration = :acc, trending_score = :score,
                        last_updated = NOW()
                """), {
                    "id": hashtag, "name": f"#{hashtag}", "count": current_count,
                    "v1d": v1d, "v7d": v7d, "v30d": v30d, "acc": acceleration, "score": trending_score
                })
            
            conn.commit()
            logger.info(f"Updated velocity for {len(hashtags)} hashtags")
    
    def _update_sound_velocities(self):
        """Update velocity scores for sounds"""
        with self.engine.connect() as conn:
            sounds = conn.execute(text("""
                SELECT DISTINCT audio_id,
                       (SELECT title FROM trend_sound_snapshots s2 
                        WHERE s2.audio_id = s.audio_id 
                        ORDER BY snapshot_at DESC LIMIT 1) as title,
                       (SELECT usage_count FROM trend_sound_snapshots s2 
                        WHERE s2.audio_id = s.audio_id 
                        ORDER BY snapshot_at DESC LIMIT 1) as current_count
                FROM trend_sound_snapshots s
                WHERE snapshot_at > NOW() - INTERVAL '7 days'
            """)).fetchall()
            
            for row in sounds:
                audio_id, title, current_count = row
                v1d = self.calculate_velocity("sound", audio_id, 24)
                v7d = self.calculate_velocity("sound", audio_id, 168)
                v30d = self.calculate_velocity("sound", audio_id, 720)
                
                acceleration = v1d - v7d
                trending_score = current_count * (1 + v7d/100) * (1 + max(0, acceleration)/100)
                
                conn.execute(text("""
                    INSERT INTO trend_velocity_scores 
                    (trend_type, trend_id, trend_name, current_count, 
                     velocity_1d, velocity_7d, velocity_30d, acceleration, trending_score, last_updated)
                    VALUES ('sound', :id, :name, :count, :v1d, :v7d, :v30d, :acc, :score, NOW())
                    ON CONFLICT (trend_type, trend_id) DO UPDATE
                    SET current_count = :count, velocity_1d = :v1d, velocity_7d = :v7d,
                        velocity_30d = :v30d, acceleration = :acc, trending_score = :score,
                        trend_name = :name, last_updated = NOW()
                """), {
                    "id": audio_id, "name": title or audio_id, "count": current_count or 0,
                    "v1d": v1d, "v7d": v7d, "v30d": v30d, "acc": acceleration, "score": trending_score
                })
            
            conn.commit()
            logger.info(f"Updated velocity for {len(sounds)} sounds")
    
    def _update_keyword_velocities(self):
        """Update velocity scores for keywords"""
        with self.engine.connect() as conn:
            keywords = conn.execute(text("""
                SELECT DISTINCT keyword, keyword_type,
                       (SELECT frequency FROM trend_keyword_snapshots s2 
                        WHERE s2.keyword = s.keyword AND s2.keyword_type = s.keyword_type
                        ORDER BY snapshot_at DESC LIMIT 1) as current_count
                FROM trend_keyword_snapshots s
                WHERE snapshot_at > NOW() - INTERVAL '7 days'
            """)).fetchall()
            
            for row in keywords:
                keyword, keyword_type, current_count = row
                trend_id = f"{keyword_type}:{keyword}"
                v1d = self.calculate_velocity("keyword", keyword, 24)
                v7d = self.calculate_velocity("keyword", keyword, 168)
                v30d = self.calculate_velocity("keyword", keyword, 720)
                
                acceleration = v1d - v7d
                trending_score = (current_count or 0) * (1 + v7d/100) * (1 + max(0, acceleration)/100)
                
                conn.execute(text("""
                    INSERT INTO trend_velocity_scores 
                    (trend_type, trend_id, trend_name, current_count, 
                     velocity_1d, velocity_7d, velocity_30d, acceleration, trending_score, last_updated)
                    VALUES ('keyword', :id, :name, :count, :v1d, :v7d, :v30d, :acc, :score, NOW())
                    ON CONFLICT (trend_type, trend_id) DO UPDATE
                    SET current_count = :count, velocity_1d = :v1d, velocity_7d = :v7d,
                        velocity_30d = :v30d, acceleration = :acc, trending_score = :score,
                        last_updated = NOW()
                """), {
                    "id": trend_id, "name": keyword, "count": current_count or 0,
                    "v1d": v1d, "v7d": v7d, "v30d": v30d, "acc": acceleration, "score": trending_score
                })
            
            conn.commit()
            logger.info(f"Updated velocity for {len(keywords)} keywords")
    
    def get_top_accelerating(
        self, 
        trend_type: str = None, 
        limit: int = 20
    ) -> List[TrendVelocity]:
        """Get trends with highest acceleration (speeding up)"""
        with self.engine.connect() as conn:
            query = """
                SELECT trend_type, trend_id, trend_name, current_count,
                       velocity_1d, velocity_7d, velocity_30d, acceleration, 
                       trending_score, last_updated
                FROM trend_velocity_scores
                WHERE acceleration > 0
            """
            if trend_type:
                query += f" AND trend_type = '{trend_type}'"
            query += f" ORDER BY acceleration DESC LIMIT {limit}"
            
            rows = conn.execute(text(query)).fetchall()
            
            return [
                TrendVelocity(
                    trend_type=r[0], trend_id=r[1], trend_name=r[2],
                    current_count=r[3], velocity_1d=r[4], velocity_7d=r[5],
                    velocity_30d=r[6], acceleration=r[7], trending_score=r[8],
                    last_updated=r[9]
                )
                for r in rows
            ]
    
    def get_top_trending(
        self,
        trend_type: str = None,
        limit: int = 20
    ) -> List[TrendVelocity]:
        """Get trends with highest trending score"""
        with self.engine.connect() as conn:
            query = """
                SELECT trend_type, trend_id, trend_name, current_count,
                       velocity_1d, velocity_7d, velocity_30d, acceleration,
                       trending_score, last_updated
                FROM trend_velocity_scores
                WHERE trending_score > 0
            """
            if trend_type:
                query += f" AND trend_type = '{trend_type}'"
            query += f" ORDER BY trending_score DESC LIMIT {limit}"

            rows = conn.execute(text(query)).fetchall()

            return [
                TrendVelocity(
                    trend_type=r[0], trend_id=r[1], trend_name=r[2],
                    current_count=r[3], velocity_1d=r[4], velocity_7d=r[5],
                    velocity_30d=r[6], acceleration=r[7], trending_score=r[8],
                    last_updated=r[9]
                )
                for r in rows
            ]

    def get_trending_hashtags(self, limit: int = 20) -> List[TrendVelocity]:
        """Get trending hashtags (IG-TREND-001 support)"""
        return self.get_top_trending(trend_type="hashtag", limit=limit)

    def get_trending_sounds(self, limit: int = 20) -> List[TrendVelocity]:
        """Get trending sounds (IG-TREND-001 support)"""
        return self.get_top_trending(trend_type="sound", limit=limit)


# Singleton
_velocity_service: Optional[TrendVelocityService] = None


def get_trend_velocity_service() -> TrendVelocityService:
    """Get singleton velocity service"""
    global _velocity_service
    if _velocity_service is None:
        _velocity_service = TrendVelocityService()
    return _velocity_service
