"""
Predictive Analytics Service
Phase 5: ML-based predictions for content performance
"""
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class PredictionType(str, Enum):
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    ENGAGEMENT_RATE = "engagement_rate"
    VIRALITY_SCORE = "virality_score"


@dataclass
class ContentFeatures:
    """Features extracted from content for prediction"""
    # Content attributes
    title_length: int = 0
    description_length: int = 0
    hashtag_count: int = 0
    has_cta: bool = False
    has_question: bool = False
    has_emoji: bool = False
    
    # Media attributes
    duration_seconds: float = 0
    is_vertical: bool = True
    has_music: bool = False
    has_text_overlay: bool = False
    
    # Timing attributes
    hour_of_day: int = 0
    day_of_week: int = 0
    is_weekend: bool = False
    
    # Historical context
    account_avg_views: float = 0
    account_follower_count: int = 0
    recent_posting_frequency: float = 0
    
    # Platform
    platform: str = "tiktok"


@dataclass
class Prediction:
    """A performance prediction"""
    prediction_type: PredictionType
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence: float
    factors: List[Dict[str, Any]]  # Contributing factors
    recommendation: str


@dataclass
class HistoricalPost:
    """Historical post data for training"""
    post_id: str
    platform: str
    features: ContentFeatures
    actual_views: int
    actual_likes: int
    actual_comments: int
    actual_shares: int
    posted_at: datetime


class PredictiveAnalyticsService:
    """
    Predicts content performance using historical data analysis.
    Uses weighted feature scoring and regression-like calculations.
    """
    
    # Feature weights for prediction (learned from typical patterns)
    FEATURE_WEIGHTS = {
        'title_length': {
            'optimal_range': (30, 60),
            'weight': 0.08,
        },
        'description_length': {
            'optimal_range': (100, 300),
            'weight': 0.05,
        },
        'hashtag_count': {
            'optimal_range': (3, 8),
            'weight': 0.06,
        },
        'has_cta': {
            'boost': 1.15,
            'weight': 0.10,
        },
        'has_question': {
            'boost': 1.12,
            'weight': 0.08,
        },
        'has_emoji': {
            'boost': 1.08,
            'weight': 0.04,
        },
        'duration_seconds': {
            'optimal_range': (15, 60),  # Short-form optimal
            'weight': 0.12,
        },
        'is_vertical': {
            'boost': 1.20,
            'weight': 0.10,
        },
        'posting_time': {
            'weight': 0.15,
        },
        'posting_frequency': {
            'optimal_range': (1, 3),  # Posts per day
            'weight': 0.07,
        },
    }
    
    # Platform-specific multipliers
    PLATFORM_MULTIPLIERS = {
        'tiktok': {'views': 1.0, 'engagement': 1.2},
        'instagram': {'views': 0.8, 'engagement': 1.0},
        'youtube': {'views': 0.6, 'engagement': 0.7},
        'twitter': {'views': 0.5, 'engagement': 0.9},
        'linkedin': {'views': 0.3, 'engagement': 0.6},
        'threads': {'views': 0.7, 'engagement': 1.1},
    }
    
    # Time-based engagement factors (hour -> multiplier)
    TIME_FACTORS = {
        0: 0.4, 1: 0.3, 2: 0.2, 3: 0.2, 4: 0.3, 5: 0.5,
        6: 0.7, 7: 0.9, 8: 1.0, 9: 0.95, 10: 0.85, 11: 0.9,
        12: 1.1, 13: 1.0, 14: 0.9, 15: 0.85, 16: 0.9, 17: 1.0,
        18: 1.15, 19: 1.2, 20: 1.15, 21: 1.0, 22: 0.8, 23: 0.6,
    }
    
    def __init__(self):
        self.historical_data: List[HistoricalPost] = []
        self.platform_baselines: Dict[str, Dict[str, float]] = {}
        self.account_baselines: Dict[str, Dict[str, float]] = {}
    
    def add_historical_data(self, post: HistoricalPost):
        """Add historical post data for learning"""
        self.historical_data.append(post)
        self._update_baselines(post)
    
    def _update_baselines(self, post: HistoricalPost):
        """Update platform and account baselines"""
        platform = post.platform.lower()
        
        if platform not in self.platform_baselines:
            self.platform_baselines[platform] = {
                'views': [], 'likes': [], 'comments': [], 'shares': []
            }
        
        self.platform_baselines[platform]['views'].append(post.actual_views)
        self.platform_baselines[platform]['likes'].append(post.actual_likes)
        self.platform_baselines[platform]['comments'].append(post.actual_comments)
        self.platform_baselines[platform]['shares'].append(post.actual_shares)
    
    def _get_baseline(self, platform: str, metric: str) -> float:
        """Get baseline value for a metric"""
        platform = platform.lower()
        
        if platform in self.platform_baselines:
            values = self.platform_baselines[platform].get(metric, [])
            if values:
                return statistics.median(values)
        
        # Default baselines
        defaults = {
            'tiktok': {'views': 5000, 'likes': 250, 'comments': 25, 'shares': 10},
            'instagram': {'views': 2000, 'likes': 150, 'comments': 15, 'shares': 5},
            'youtube': {'views': 1000, 'likes': 50, 'comments': 10, 'shares': 3},
            'twitter': {'views': 500, 'likes': 25, 'comments': 5, 'shares': 3},
            'linkedin': {'views': 300, 'likes': 20, 'comments': 5, 'shares': 2},
            'threads': {'views': 1500, 'likes': 100, 'comments': 10, 'shares': 5},
        }
        
        return defaults.get(platform, defaults['tiktok']).get(metric, 1000)
    
    def extract_features(
        self,
        title: str,
        description: str,
        hashtags: List[str],
        duration_seconds: float,
        platform: str,
        posting_time: Optional[datetime] = None,
        account_followers: int = 0,
        recent_avg_views: float = 0
    ) -> ContentFeatures:
        """Extract features from content"""
        posting_time = posting_time or datetime.utcnow()
        
        return ContentFeatures(
            title_length=len(title),
            description_length=len(description),
            hashtag_count=len(hashtags),
            has_cta=any(cta in description.lower() for cta in 
                       ['link in bio', 'follow', 'subscribe', 'comment', 'share', 'like']),
            has_question='?' in title or '?' in description,
            has_emoji=any(ord(c) > 127 for c in title + description),
            duration_seconds=duration_seconds,
            is_vertical=True,  # Assume vertical for short-form
            hour_of_day=posting_time.hour,
            day_of_week=posting_time.weekday(),
            is_weekend=posting_time.weekday() >= 5,
            account_avg_views=recent_avg_views or self._get_baseline(platform, 'views'),
            account_follower_count=account_followers,
            platform=platform.lower()
        )
    
    def _calculate_feature_score(self, features: ContentFeatures) -> float:
        """Calculate overall feature score (0-1)"""
        score = 0.5  # Base score
        factors = []
        
        # Title length
        if self._in_optimal_range(
            features.title_length, 
            self.FEATURE_WEIGHTS['title_length']['optimal_range']
        ):
            score += 0.05
            factors.append(('title_length', 'optimal', 0.05))
        
        # Description length
        if self._in_optimal_range(
            features.description_length,
            self.FEATURE_WEIGHTS['description_length']['optimal_range']
        ):
            score += 0.03
            factors.append(('description_length', 'optimal', 0.03))
        
        # Hashtags
        if self._in_optimal_range(
            features.hashtag_count,
            self.FEATURE_WEIGHTS['hashtag_count']['optimal_range']
        ):
            score += 0.04
            factors.append(('hashtag_count', 'optimal', 0.04))
        
        # CTA boost
        if features.has_cta:
            boost = 0.08
            score += boost
            factors.append(('has_cta', True, boost))
        
        # Question boost
        if features.has_question:
            boost = 0.06
            score += boost
            factors.append(('has_question', True, boost))
        
        # Duration
        if self._in_optimal_range(
            features.duration_seconds,
            self.FEATURE_WEIGHTS['duration_seconds']['optimal_range']
        ):
            score += 0.08
            factors.append(('duration', 'optimal', 0.08))
        
        # Vertical format
        if features.is_vertical:
            score += 0.05
            factors.append(('is_vertical', True, 0.05))
        
        # Time factor
        time_mult = self.TIME_FACTORS.get(features.hour_of_day, 0.7)
        time_boost = (time_mult - 0.7) * 0.2
        score += time_boost
        factors.append(('posting_time', features.hour_of_day, time_boost))
        
        # Weekend factor (slight negative for most platforms)
        if features.is_weekend and features.platform not in ('instagram', 'tiktok'):
            score -= 0.03
            factors.append(('is_weekend', True, -0.03))
        
        return min(1.0, max(0.0, score)), factors
    
    def _in_optimal_range(self, value: float, range_tuple: Tuple[float, float]) -> bool:
        """Check if value is in optimal range"""
        return range_tuple[0] <= value <= range_tuple[1]
    
    def predict_views(self, features: ContentFeatures) -> Prediction:
        """Predict view count for content"""
        baseline = self._get_baseline(features.platform, 'views')
        
        # Use account average if available
        if features.account_avg_views > 0:
            baseline = features.account_avg_views
        
        # Calculate feature score
        feature_score, factors = self._calculate_feature_score(features)
        
        # Apply platform multiplier
        platform_mult = self.PLATFORM_MULTIPLIERS.get(
            features.platform, {'views': 1.0}
        )['views']
        
        # Calculate prediction
        # Score of 0.5 = baseline, higher/lower adjusts proportionally
        multiplier = 0.5 + feature_score  # 0.5 to 1.5 range
        predicted = baseline * multiplier * platform_mult
        
        # Confidence interval (wider for lower confidence)
        confidence = self._calculate_confidence(features)
        margin = predicted * (1 - confidence) * 0.5
        
        # Factor analysis
        factor_details = [
            {
                'factor': f[0],
                'value': f[1],
                'impact': f[2],
                'impact_percent': f[2] / feature_score * 100 if feature_score > 0 else 0
            }
            for f in factors
        ]
        
        recommendation = self._generate_recommendation(factors, features, 'views')
        
        return Prediction(
            prediction_type=PredictionType.VIEWS,
            predicted_value=round(predicted),
            confidence_interval=(round(predicted - margin), round(predicted + margin)),
            confidence=confidence,
            factors=factor_details,
            recommendation=recommendation
        )
    
    def predict_engagement(self, features: ContentFeatures) -> Dict[str, Prediction]:
        """Predict all engagement metrics"""
        views_pred = self.predict_views(features)
        predicted_views = views_pred.predicted_value
        
        # Derive other metrics from views
        platform = features.platform.lower()
        
        # Typical engagement ratios
        ratios = {
            'tiktok': {'likes': 0.05, 'comments': 0.005, 'shares': 0.002},
            'instagram': {'likes': 0.08, 'comments': 0.008, 'shares': 0.003},
            'youtube': {'likes': 0.04, 'comments': 0.003, 'shares': 0.001},
            'twitter': {'likes': 0.03, 'comments': 0.01, 'shares': 0.005},
            'linkedin': {'likes': 0.06, 'comments': 0.015, 'shares': 0.008},
            'threads': {'likes': 0.07, 'comments': 0.006, 'shares': 0.002},
        }
        
        platform_ratios = ratios.get(platform, ratios['tiktok'])
        
        # Adjust ratios based on features
        if features.has_question:
            platform_ratios['comments'] *= 1.5
        if features.has_cta:
            platform_ratios['shares'] *= 1.3
        
        predictions = {'views': views_pred}
        
        for metric, ratio in platform_ratios.items():
            pred_value = predicted_views * ratio
            confidence = views_pred.confidence * 0.9  # Slightly lower confidence
            margin = pred_value * (1 - confidence) * 0.5
            
            predictions[metric] = Prediction(
                prediction_type=PredictionType(metric),
                predicted_value=round(pred_value),
                confidence_interval=(round(max(0, pred_value - margin)), round(pred_value + margin)),
                confidence=confidence,
                factors=views_pred.factors,
                recommendation=self._generate_recommendation([], features, metric)
            )
        
        return predictions
    
    def predict_virality_score(self, features: ContentFeatures) -> Prediction:
        """Predict virality potential (0-100 score)"""
        feature_score, factors = self._calculate_feature_score(features)
        
        # Virality factors
        virality_score = feature_score * 100
        
        # Boost for viral indicators
        viral_boost = 0
        
        # Short duration is viral
        if 15 <= features.duration_seconds <= 30:
            viral_boost += 10
            factors.append(('short_duration', True, 10))
        
        # Questions drive comments which drive algorithm
        if features.has_question:
            viral_boost += 8
        
        # CTAs drive engagement
        if features.has_cta:
            viral_boost += 5
        
        # Prime time posting
        if features.hour_of_day in (19, 20, 21):
            viral_boost += 7
        
        virality_score = min(100, virality_score + viral_boost)
        
        confidence = self._calculate_confidence(features)
        
        # Categorize
        if virality_score >= 80:
            recommendation = "High viral potential! Post during peak hours for maximum reach."
        elif virality_score >= 60:
            recommendation = "Good potential. Consider adding a stronger hook or question."
        elif virality_score >= 40:
            recommendation = "Moderate potential. Review top factors and optimize."
        else:
            recommendation = "Lower potential. Consider significant content adjustments."
        
        return Prediction(
            prediction_type=PredictionType.VIRALITY_SCORE,
            predicted_value=round(virality_score),
            confidence_interval=(max(0, virality_score - 15), min(100, virality_score + 15)),
            confidence=confidence,
            factors=[{'factor': f[0], 'value': f[1], 'impact': f[2]} for f in factors],
            recommendation=recommendation
        )
    
    def _calculate_confidence(self, features: ContentFeatures) -> float:
        """Calculate prediction confidence based on data quality"""
        confidence = 0.5  # Base confidence
        
        # More historical data = higher confidence
        platform_data = [p for p in self.historical_data if p.platform == features.platform]
        if len(platform_data) > 100:
            confidence += 0.25
        elif len(platform_data) > 50:
            confidence += 0.15
        elif len(platform_data) > 20:
            confidence += 0.08
        
        # Account history improves confidence
        if features.account_avg_views > 0:
            confidence += 0.1
        
        # Known optimal features increase confidence
        if features.is_vertical:
            confidence += 0.03
        if 15 <= features.duration_seconds <= 120:
            confidence += 0.05
        
        return min(0.95, confidence)
    
    def _generate_recommendation(
        self,
        factors: List[Tuple],
        features: ContentFeatures,
        metric: str
    ) -> str:
        """Generate actionable recommendation"""
        recommendations = []
        
        # Check for improvements
        if features.title_length < 30:
            recommendations.append("Consider a longer, more descriptive title (30-60 chars)")
        elif features.title_length > 80:
            recommendations.append("Title may be too long - aim for 30-60 characters")
        
        if features.hashtag_count < 3:
            recommendations.append("Add more relevant hashtags (3-8 optimal)")
        elif features.hashtag_count > 15:
            recommendations.append("Consider fewer, more targeted hashtags")
        
        if not features.has_cta:
            recommendations.append("Add a call-to-action to boost engagement")
        
        if not features.has_question:
            recommendations.append("Ask a question to encourage comments")
        
        if features.duration_seconds > 60 and features.platform in ('tiktok', 'instagram'):
            recommendations.append("Consider shorter content (15-60s) for better retention")
        
        if features.hour_of_day not in (7, 8, 12, 13, 18, 19, 20, 21):
            recommendations.append("Consider posting during peak hours (7-9am, 12-1pm, 6-9pm)")
        
        if recommendations:
            return recommendations[0]  # Return top recommendation
        
        return f"Content is well-optimized for {metric}. Monitor performance."
    
    def get_content_score(
        self,
        title: str,
        description: str,
        hashtags: List[str],
        duration_seconds: float,
        platform: str,
        posting_time: Optional[datetime] = None
    ) -> Dict:
        """Get comprehensive content score and predictions"""
        features = self.extract_features(
            title=title,
            description=description,
            hashtags=hashtags,
            duration_seconds=duration_seconds,
            platform=platform,
            posting_time=posting_time
        )
        
        virality = self.predict_virality_score(features)
        engagement = self.predict_engagement(features)
        
        return {
            'overall_score': virality.predicted_value,
            'confidence': virality.confidence,
            'predictions': {
                'views': engagement['views'].predicted_value,
                'likes': engagement['likes'].predicted_value,
                'comments': engagement['comments'].predicted_value,
                'shares': engagement['shares'].predicted_value,
            },
            'factors': virality.factors,
            'recommendations': [
                virality.recommendation,
                engagement['views'].recommendation,
            ],
            'optimal_posting_times': self._get_optimal_times(features.platform),
        }
    
    def _get_optimal_times(self, platform: str) -> List[str]:
        """Get optimal posting times for platform"""
        peak_hours = [h for h, m in self.TIME_FACTORS.items() if m >= 1.0]
        return [f"{h}:00" for h in sorted(peak_hours)]


# Singleton instance
predictive_analytics = PredictiveAnalyticsService()
