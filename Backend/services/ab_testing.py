"""
A/B Testing Framework
Phase 5: Test content variations and optimize based on performance
"""
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import statistics
import math


class TestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariationType(str, Enum):
    TITLE = "title"
    DESCRIPTION = "description"
    HASHTAGS = "hashtags"
    THUMBNAIL = "thumbnail"
    POSTING_TIME = "posting_time"
    CAPTION_LENGTH = "caption_length"
    CTA_STYLE = "cta_style"
    HOOK_TYPE = "hook_type"


@dataclass
class Variation:
    """A single variation in an A/B test"""
    id: str
    name: str
    variation_type: VariationType
    content: Any  # The actual variation content
    is_control: bool = False
    impressions: int = 0
    conversions: int = 0  # Could be views, likes, etc.
    engagement_sum: float = 0.0
    sample_size: int = 0
    
    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.impressions if self.impressions > 0 else 0
    
    @property
    def avg_engagement(self) -> float:
        return self.engagement_sum / self.sample_size if self.sample_size > 0 else 0


@dataclass
class ABTest:
    """An A/B test configuration"""
    id: str
    name: str
    description: str
    variation_type: VariationType
    variations: List[Variation]
    status: TestStatus = TestStatus.DRAFT
    platform: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_sample_size: int = 100
    confidence_level: float = 0.95
    created_at: datetime = field(default_factory=datetime.utcnow)
    winner_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of statistical analysis"""
    test_id: str
    winner_variation_id: Optional[str]
    confidence: float
    is_significant: bool
    lift: float  # Percentage improvement
    p_value: float
    sample_sizes: Dict[str, int]
    conversion_rates: Dict[str, float]
    recommendation: str


class ABTestingService:
    """
    Manages A/B tests for content optimization.
    Supports multiple variation types and statistical significance testing.
    """
    
    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.assignments: Dict[str, str] = {}  # user_id -> variation_id
    
    def create_test(
        self,
        name: str,
        description: str,
        variation_type: VariationType,
        variations: List[Dict[str, Any]],
        platform: Optional[str] = None,
        min_sample_size: int = 100,
        confidence_level: float = 0.95
    ) -> ABTest:
        """
        Create a new A/B test.
        
        Args:
            name: Test name
            description: Test description
            variation_type: Type of variation being tested
            variations: List of variation configs with 'name' and 'content'
            platform: Target platform (optional)
            min_sample_size: Minimum samples per variation
            confidence_level: Required confidence for significance
        
        Returns:
            Created ABTest
        """
        test_id = str(uuid4())
        
        # Create variations
        test_variations = []
        for i, var_config in enumerate(variations):
            variation = Variation(
                id=str(uuid4()),
                name=var_config.get('name', f'Variation {i+1}'),
                variation_type=variation_type,
                content=var_config['content'],
                is_control=(i == 0)  # First variation is control
            )
            test_variations.append(variation)
        
        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            variation_type=variation_type,
            variations=test_variations,
            platform=platform,
            min_sample_size=min_sample_size,
            confidence_level=confidence_level
        )
        
        self.tests[test_id] = test
        return test
    
    def start_test(self, test_id: str, duration_days: Optional[int] = None) -> ABTest:
        """Start an A/B test"""
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        test.status = TestStatus.RUNNING
        test.start_date = datetime.utcnow()
        
        if duration_days:
            test.end_date = test.start_date + timedelta(days=duration_days)
        
        return test
    
    def pause_test(self, test_id: str) -> ABTest:
        """Pause a running test"""
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        test.status = TestStatus.PAUSED
        return test
    
    def stop_test(self, test_id: str) -> ABTest:
        """Stop and complete a test"""
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.utcnow()
        
        # Determine winner
        result = self.analyze_test(test_id)
        if result.is_significant:
            test.winner_id = result.winner_variation_id
        
        return test
    
    def get_variation(
        self,
        test_id: str,
        user_id: str,
        content_id: Optional[str] = None
    ) -> Variation:
        """
        Get a variation for a user (deterministic assignment).
        Uses consistent hashing for stable assignment.
        """
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        
        if test.status != TestStatus.RUNNING:
            # Return control if test not running
            return test.variations[0]
        
        # Deterministic assignment based on user_id and test_id
        assignment_key = f"{user_id}:{test_id}:{content_id or ''}"
        hash_value = int(hashlib.md5(assignment_key.encode()).hexdigest(), 16)
        variation_index = hash_value % len(test.variations)
        
        variation = test.variations[variation_index]
        
        # Track assignment
        self.assignments[assignment_key] = variation.id
        
        return variation
    
    def record_impression(self, test_id: str, variation_id: str):
        """Record an impression for a variation"""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variation in test.variations:
            if variation.id == variation_id:
                variation.impressions += 1
                break
    
    def record_conversion(
        self,
        test_id: str,
        variation_id: str,
        engagement_value: float = 1.0
    ):
        """Record a conversion/engagement for a variation"""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variation in test.variations:
            if variation.id == variation_id:
                variation.conversions += 1
                variation.engagement_sum += engagement_value
                variation.sample_size += 1
                break
    
    def analyze_test(self, test_id: str) -> TestResult:
        """
        Perform statistical analysis on test results.
        Uses Z-test for proportions.
        """
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        
        if len(test.variations) < 2:
            raise ValueError("Need at least 2 variations for analysis")
        
        # Get control and best treatment
        control = test.variations[0]
        treatments = test.variations[1:]
        
        best_treatment = max(treatments, key=lambda v: v.conversion_rate)
        
        # Calculate statistics
        sample_sizes = {v.id: v.impressions for v in test.variations}
        conversion_rates = {v.id: v.conversion_rate for v in test.variations}
        
        # Z-test for proportions
        p1 = control.conversion_rate
        p2 = best_treatment.conversion_rate
        n1 = control.impressions
        n2 = best_treatment.impressions
        
        # Check minimum sample size
        min_samples_met = all(
            v.impressions >= test.min_sample_size 
            for v in test.variations
        )
        
        if n1 == 0 or n2 == 0:
            return TestResult(
                test_id=test_id,
                winner_variation_id=None,
                confidence=0,
                is_significant=False,
                lift=0,
                p_value=1.0,
                sample_sizes=sample_sizes,
                conversion_rates=conversion_rates,
                recommendation="Insufficient data to determine winner"
            )
        
        # Pooled proportion
        p_pooled = (control.conversions + best_treatment.conversions) / (n1 + n2)
        
        # Standard error
        if p_pooled == 0 or p_pooled == 1:
            se = 0.0001  # Avoid division by zero
        else:
            se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
        
        # Z-score
        z_score = (p2 - p1) / se if se > 0 else 0
        
        # P-value (two-tailed)
        p_value = 2 * (1 - self._normal_cdf(abs(z_score)))
        
        # Confidence
        confidence = 1 - p_value
        
        # Lift (improvement)
        lift = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
        
        # Determine significance
        is_significant = (
            p_value < (1 - test.confidence_level) and
            min_samples_met
        )
        
        # Winner determination
        winner_id = None
        if is_significant:
            if p2 > p1:
                winner_id = best_treatment.id
            else:
                winner_id = control.id
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            is_significant, lift, min_samples_met, 
            control, best_treatment, test
        )
        
        return TestResult(
            test_id=test_id,
            winner_variation_id=winner_id,
            confidence=confidence,
            is_significant=is_significant,
            lift=lift,
            p_value=p_value,
            sample_sizes=sample_sizes,
            conversion_rates=conversion_rates,
            recommendation=recommendation
        )
    
    def _normal_cdf(self, x: float) -> float:
        """Cumulative distribution function for standard normal"""
        return (1 + math.erf(x / math.sqrt(2))) / 2
    
    def _generate_recommendation(
        self,
        is_significant: bool,
        lift: float,
        min_samples_met: bool,
        control: Variation,
        treatment: Variation,
        test: ABTest
    ) -> str:
        """Generate human-readable recommendation"""
        if not min_samples_met:
            needed = test.min_sample_size - min(control.impressions, treatment.impressions)
            return f"Continue test. Need ~{needed} more samples for statistical significance."
        
        if not is_significant:
            return "No significant difference detected. Consider extending test or trying larger variations."
        
        if lift > 0:
            return f"'{treatment.name}' outperforms control by {lift:.1f}%. Recommend implementing this variation."
        else:
            return f"Control outperforms '{treatment.name}' by {abs(lift):.1f}%. Keep current approach."
    
    def get_active_tests(self, platform: Optional[str] = None) -> List[ABTest]:
        """Get all active tests, optionally filtered by platform"""
        tests = [t for t in self.tests.values() if t.status == TestStatus.RUNNING]
        if platform:
            tests = [t for t in tests if t.platform is None or t.platform == platform]
        return tests
    
    def get_test_summary(self, test_id: str) -> Dict:
        """Get summary of test progress"""
        if test_id not in self.tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.tests[test_id]
        
        total_impressions = sum(v.impressions for v in test.variations)
        total_conversions = sum(v.conversions for v in test.variations)
        
        variation_summaries = []
        for v in test.variations:
            variation_summaries.append({
                'id': v.id,
                'name': v.name,
                'is_control': v.is_control,
                'impressions': v.impressions,
                'conversions': v.conversions,
                'conversion_rate': v.conversion_rate,
                'avg_engagement': v.avg_engagement,
            })
        
        # Progress toward minimum sample
        progress = min(
            v.impressions / test.min_sample_size 
            for v in test.variations
        ) if test.variations else 0
        
        return {
            'test_id': test_id,
            'name': test.name,
            'status': test.status.value,
            'variation_type': test.variation_type.value,
            'total_impressions': total_impressions,
            'total_conversions': total_conversions,
            'variations': variation_summaries,
            'progress_percent': min(100, progress * 100),
            'days_running': (datetime.utcnow() - test.start_date).days if test.start_date else 0,
            'winner_id': test.winner_id,
        }


# Pre-built test templates
class TestTemplates:
    """Common A/B test templates"""
    
    @staticmethod
    def title_length_test(
        short_title: str,
        long_title: str
    ) -> Dict:
        """Test short vs long titles"""
        return {
            'name': 'Title Length Test',
            'description': 'Compare short punchy titles vs longer descriptive titles',
            'variation_type': VariationType.TITLE,
            'variations': [
                {'name': 'Short Title (Control)', 'content': short_title},
                {'name': 'Long Title', 'content': long_title},
            ]
        }
    
    @staticmethod
    def hook_style_test(hooks: List[str]) -> Dict:
        """Test different hook styles"""
        variations = [
            {'name': f'Hook {i+1}', 'content': hook}
            for i, hook in enumerate(hooks)
        ]
        return {
            'name': 'Hook Style Test',
            'description': 'Compare different opening hooks for engagement',
            'variation_type': VariationType.HOOK_TYPE,
            'variations': variations
        }
    
    @staticmethod
    def hashtag_strategy_test(
        minimal: List[str],
        moderate: List[str],
        aggressive: List[str]
    ) -> Dict:
        """Test hashtag strategies"""
        return {
            'name': 'Hashtag Strategy Test',
            'description': 'Compare different hashtag quantities and types',
            'variation_type': VariationType.HASHTAGS,
            'variations': [
                {'name': 'Minimal (3-5)', 'content': minimal},
                {'name': 'Moderate (10-15)', 'content': moderate},
                {'name': 'Aggressive (25+)', 'content': aggressive},
            ]
        }
    
    @staticmethod
    def posting_time_test(times: List[str]) -> Dict:
        """Test different posting times"""
        variations = [
            {'name': f'Post at {time}', 'content': time}
            for time in times
        ]
        return {
            'name': 'Posting Time Test',
            'description': 'Find optimal posting times for your audience',
            'variation_type': VariationType.POSTING_TIME,
            'variations': variations
        }


# Singleton instance
ab_testing_service = ABTestingService()
