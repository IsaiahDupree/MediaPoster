"""
Sentiment Analysis with multiple backend support
Supports: VADER (simple), Transformers (local), OpenAI (cloud)
"""
from typing import Dict, List, Any, Optional
from loguru import logger
import os


class SentimentAnalyzer:
    """Analyze sentiment using configurable backend"""
    
    def __init__(self, backend: str = "vader"):
        """
        Initialize sentiment analyzer
        
        Args:
            backend: 'vader', 'transformers', or 'openai'
        """
        self.backend = backend
        self.analyzer = None
        
        if backend == "vader":
            self._init_vader()
        elif backend == "transformers":
            self._init_transformers()
        elif backend == "openai":
            self._init_openai()
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        logger.info(f"Sentiment analyzer initialized: {backend}")
    
    def _init_vader(self):
        """Initialize VADER (simple, fast, no ML)"""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER initialized")
        except ImportError:
            logger.error("vaderSentiment not installed. Run: pip install vaderSentiment")
            raise
    
    def _init_transformers(self):
        """Initialize Hugging Face transformers (local ML)"""
        try:
            from transformers import pipeline
            self.analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english"
            )
            logger.info("Transformers model loaded")
        except ImportError:
            logger.error("transformers not installed. Run: pip install transformers torch")
            raise
    
    def _init_openai(self):
        """Initialize OpenAI (cloud API)"""
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            self.analyzer = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
            raise
    
    def analyze_comment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of single comment
        
        Args:
            text: Comment text
            
        Returns:
            {
                'sentiment': 'positive' | 'negative' | 'neutral',
                'score': float (-1 to 1),
                'confidence': float (0 to 1)
            }
        """
        if not text or not text.strip():
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0
            }
        
        if self.backend == "vader":
            return self._analyze_vader(text)
        elif self.backend == "transformers":
            return self._analyze_transformers(text)
        elif self.backend == "openai":
            return self._analyze_openai(text)
    
    def _analyze_vader(self, text: str) -> Dict[str, Any]:
        """Analyze with VADER"""
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        # Classify based on compound score
        if compound >= 0.05:
            sentiment = 'positive'
        elif compound <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': compound,  # -1 to 1
            'confidence': abs(compound),
            'raw': scores
        }
    
    def _analyze_transformers(self, text: str) -> Dict[str, Any]:
        """Analyze with transformers"""
        # Truncate long text
        text = text[:512]
        
        result = self.analyzer(text)[0]
        label = result['label'].lower()  # POSITIVE, NEGATIVE
        confidence = result['score']
        
        # Map to sentiment
        if label == 'positive':
            sentiment = 'positive'
            score = confidence
        elif label == 'negative':
            sentiment = 'negative'
            score = -confidence
        else:
            sentiment = 'neutral'
            score = 0.0
        
        return {
            'sentiment': sentiment,
            'score': score,
            'confidence': confidence,
            'raw': result
        }
    
    def _analyze_openai(self, text: str) -> Dict[str, Any]:
        """Analyze with OpenAI"""
        try:
            response = self.analyzer.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the following comment. Respond with only: POSITIVE, NEGATIVE, or NEUTRAL"
                    },
                    {
                        "role": "user",
                        "content": text[:500]  # Truncate
                    }
                ],
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            sentiment_map = {
                'POSITIVE': ('positive', 0.8),
                'NEGATIVE': ('negative', -0.8),
                'NEUTRAL': ('neutral', 0.0)
            }
            
            sentiment, score = sentiment_map.get(result, ('neutral', 0.0))
            
            return {
                'sentiment': sentiment,
                'score': score,
                'confidence': 0.9,  # OpenAI generally high confidence
                'raw': result
            }
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def analyze_batch(self, comments: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple comments"""
        return [self.analyze_comment(c) for c in comments]
    
    def get_overall_sentiment(self, comments: List[str]) -> Dict[str, Any]:
        """
        Get aggregated sentiment for all comments
        
        Returns:
            {
                'sentiment_score': float (-1 to 1),
                'positive_pct': float (0-100),
                'negative_pct': float,
                'neutral_pct': float,
                'total_comments': int
            }
        """
        if not comments:
            return {
                'sentiment_score': 0.0,
                'positive_pct': 0.0,
                'negative_pct': 0.0,
                'neutral_pct': 0.0,
                'total_comments': 0
            }
        
        results = self.analyze_batch(comments)
        
        total = len(results)
        positive = sum(1 for r in results if r['sentiment'] == 'positive')
        negative = sum(1 for r in results if r['sentiment'] == 'negative')
        neutral = total - positive - negative
        
        # Average score
        avg_score = sum(r['score'] for r in results) / total if total > 0 else 0.0
        
        return {
            'sentiment_score': avg_score,
            'positive_pct': (positive / total * 100) if total > 0 else 0.0,
            'negative_pct': (negative / total * 100) if total > 0 else 0.0,
            'neutral_pct': (neutral / total * 100) if total > 0 else 0.0,
            'total_comments': total
        }


# Example usage
if __name__ == '__main__':
    # Test comments
    test_comments = [
        "This is amazing! Love it! 🔥",
        "Not sure about this...",
        "Terrible quality, waste of time",
        "Pretty good tutorial, thanks!",
        "BEST VIDEO EVER!!! ❤️❤️❤️",
        "Meh, could be better",
        "Awesome content, keep it up!"
    ]
    
    # Test each backend
    for backend in ['vader', 'transformers']:
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Testing {backend.upper()} backend")
            logger.info(f"{'='*80}")
            
            analyzer = SentimentAnalyzer(backend=backend)
            
            # Analyze individual comments
            logger.info("\nIndividual Results:")
            for comment in test_comments[:3]:
                result = analyzer.analyze_comment(comment)
                logger.info(f"\n  '{comment}'")
                logger.info(f"  → {result['sentiment']} (score: {result['score']:.2f})")
            
            # Overall sentiment
            overall = analyzer.get_overall_sentiment(test_comments)
            logger.info(f"\nOverall Sentiment:")
            logger.info(f"  Score: {overall['sentiment_score']:.2f}")
            logger.info(f"  Positive: {overall['positive_pct']:.1f}%")
            logger.info(f"  Negative: {overall['negative_pct']:.1f}%")
            logger.info(f"  Neutral: {overall['neutral_pct']:.1f}%")
            
        except Exception as e:
            logger.error(f"Failed to test {backend}: {e}")
