"""
Word-Level Transcript Analyzer

Analyzes transcripts at the word level to identify:
- Speech functions (greeting, pain_point, cta, proof, etc.)
- Emphasis words (power words, emotional triggers)
- CTA keywords
- Sentiment per word
- Question detection
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class SpeechFunction(str, Enum):
    """Types of speech functions for content analysis"""
    GREETING = "greeting"
    PAIN_POINT = "pain_point"
    SOLUTION_INTRO = "solution_intro"
    TOPIC = "topic"
    CTA_INTRO = "cta_intro"
    CTA_ACTION = "cta_action"
    PROOF = "proof"
    BENEFIT = "benefit"
    OBJECTION_HANDLE = "objection_handle"
    AUTHORITY = "authority"
    URGENCY = "urgency"
    CURIOSITY = "curiosity"
    TRANSITION = "transition"


@dataclass
class WordAnalysis:
    """Analysis results for a single word"""
    word: str
    word_index: int
    start_s: float
    end_s: float
    is_emphasis: bool = False
    is_question: bool = False
    is_cta_keyword: bool = False
    speech_function: Optional[str] = None
    sentiment_score: Optional[float] = None
    emotion: Optional[str] = None


class WordAnalyzer:
    """Analyzes transcripts at word level"""
    
    # Power words that typically indicate emphasis
    EMPHASIS_WORDS = {
        # Pain words
        'struggling', 'frustrated', 'tired', 'stuck', 'confused', 'overwhelmed',
        'problem', 'issue', 'mistake', 'wrong', 'fail', 'failing', 'waste',
        
        # Solution words
        'solution', 'fix', 'solve', 'easy', 'simple', 'quick', 'fast', 'instant',
        'secret', 'trick', 'hack', 'proven', 'guaranteed', 'works',
        
        # Authority words
        'expert', 'professional', 'certified', 'proven', 'tested', 'research',
        'science', 'study', 'data',
        
        # Emotion words
        'amazing', 'incredible', 'awesome', 'perfect', 'beautiful', 'love',
        'hate', 'fear', 'worry', 'excited', 'thrilled',
        
        # Urgency words
        'now', 'today', 'immediately', 'urgent', 'limited', 'exclusive',
        'first', 'only', 'never', 'always',
        
        # Curiosity words
        'discover', 'reveal', 'secret', 'hidden', 'unknown', 'surprising',
        'shocking', 'weird', 'strange',
    }
    
    # CTA keywords
    CTA_KEYWORDS = {
        'click', 'subscribe', 'follow', 'like', 'comment', 'share', 'download',
        'buy', 'purchase', 'order', 'get', 'grab', 'join', 'sign', 'register',
        'learn', 'discover', 'watch', 'check', 'visit', 'try', 'start',
    }
    
    # Greeting patterns
    GREETING_WORDS = {
        'hey', 'hi', 'hello', 'welcome', 'greetings', 'sup', 'yo',
    }
    
    # Pain point indicators
    PAIN_WORDS = {
        'struggling', 'frustrated', 'tired', 'stuck', 'confused', 'overwhelmed',
        'problem', 'issue', 'mistake', 'wrong', 'fail', 'failing', 'waste',
        'annoying', 'difficult', 'hard', 'impossible', 'never',
    }
    
    # Solution indicators
    SOLUTION_WORDS = {
        'solution', 'fix', 'solve', 'answer', 'way', 'method', 'system',
        'formula', 'framework', 'strategy', 'approach',
    }
    
    # Proof indicators
    PROOF_WORDS = {
        'proof', 'evidence', 'results', 'data', 'study', 'research',
        'tested', 'proven', 'verified', 'confirmed', 'statistics',
    }
    
    # Positive sentiment words
    POSITIVE_WORDS = {
        'good', 'great', 'amazing', 'awesome', 'perfect', 'excellent',
        'wonderful', 'fantastic', 'love', 'beautiful', 'best', 'better',
        'easy', 'simple', 'quick', 'fast', 'effective', 'powerful',
    }
    
    # Negative sentiment words
    NEGATIVE_WORDS = {
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'never',
        'problem', 'issue', 'mistake', 'wrong', 'fail', 'waste', 'difficult',
        'hard', 'impossible', 'frustrated', 'annoying',
    }
    
    def __init__(self):
        """Initialize word analyzer"""
        pass
    
    def analyze_word(
        self, 
        word: str, 
        word_index: int,
        start_s: float,
        end_s: float,
        context_before: List[str] = None,
        context_after: List[str] = None
    ) -> WordAnalysis:
        """
        Analyze a single word with context
        
        Args:
            word: The word to analyze
            word_index: Position in transcript
            start_s: Start time in seconds
            end_s: End time in seconds
            context_before: Previous words for context (optional)
            context_after: Following words for context (optional)
            
        Returns:
            WordAnalysis with all features
        """
        word_lower = word.lower().strip('.,!?;:')
        
        # Initialize analysis
        analysis = WordAnalysis(
            word=word,
            word_index=word_index,
            start_s=start_s,
            end_s=end_s
        )
        
        # Check if emphasis word
        analysis.is_emphasis = word_lower in self.EMPHASIS_WORDS
        
        # Check if CTA keyword
        analysis.is_cta_keyword = word_lower in self.CTA_KEYWORDS
        
        # Detect speech function
        analysis.speech_function = self._detect_speech_function(
            word_lower, 
            context_before, 
            context_after
        )
        
        # Calculate sentiment
        analysis.sentiment_score = self._calculate_sentiment(word_lower)
        
        # Detect emotion
        analysis.emotion = self._detect_emotion(word_lower)
        
        # Check if part of question
        analysis.is_question = self._is_question(word, context_after)
        
        return analysis
    
    def analyze_transcript(
        self, 
        words: List[Dict[str, any]]
    ) -> List[WordAnalysis]:
        """
        Analyze entire transcript
        
        Args:
            words: List of word dicts with 'word', 'start', 'end'
            
        Returns:
            List of WordAnalysis objects
        """
        analyses = []
        
        for i, word_dict in enumerate(words):
            # Get context windows
            context_before = [
                words[j]['word'] 
                for j in range(max(0, i-3), i)
            ] if i > 0 else []
            
            context_after = [
                words[j]['word'] 
                for j in range(i+1, min(len(words), i+4))
            ] if i < len(words) - 1 else []
            
            # Analyze word
            analysis = self.analyze_word(
                word=word_dict['word'],
                word_index=i,
                start_s=word_dict['start'],
                end_s=word_dict['end'],
                context_before=context_before,
                context_after=context_after
            )
            
            analyses.append(analysis)
        
        return analyses
    
    def _detect_speech_function(
        self, 
        word: str, 
        context_before: List[str],
        context_after: List[str]
    ) -> Optional[str]:
        """Detect the speech function of a word"""
        
        # Greeting (usually at start)
        if word in self.GREETING_WORDS:
            return SpeechFunction.GREETING
        
        # Pain point
        if word in self.PAIN_WORDS:
            return SpeechFunction.PAIN_POINT
        
        # Solution intro
        if word in self.SOLUTION_WORDS:
            return SpeechFunction.SOLUTION_INTRO
        
        # CTA intro phrases
        if word == 'here' and context_after and context_after[0].lower() == 'is':
            return SpeechFunction.CTA_INTRO
        if word == 'how' and context_before and context_before[-1].lower() == 'is':
            return SpeechFunction.CTA_INTRO
        
        # CTA action
        if word in self.CTA_KEYWORDS:
            return SpeechFunction.CTA_ACTION
        
        # Proof
        if word in self.PROOF_WORDS:
            return SpeechFunction.PROOF
        
        return None
    
    def _calculate_sentiment(self, word: str) -> Optional[float]:
        """
        Calculate sentiment score for word
        
        Returns:
            Float between -1.0 (negative) and 1.0 (positive)
        """
        if word in self.POSITIVE_WORDS:
            return 0.8
        elif word in self.NEGATIVE_WORDS:
            return -0.8
        elif word in self.PAIN_WORDS:
            return -0.6
        elif word in self.SOLUTION_WORDS:
            return 0.6
        
        return 0.0  # Neutral
    
    def _detect_emotion(self, word: str) -> Optional[str]:
        """Detect primary emotion conveyed by word"""
        
        emotion_map = {
            'love': 'joy',
            'hate': 'anger',
            'fear': 'fear',
            'excited': 'joy',
            'frustrated': 'anger',
            'worried': 'fear',
            'amazing': 'joy',
            'terrible': 'anger',
            'scared': 'fear',
        }
        
        return emotion_map.get(word)
    
    def _is_question(self, word: str, context_after: List[str]) -> bool:
        """Check if word is part of a question"""
        
        # Check for question mark
        if '?' in word:
            return True
        
        # Check for question words
        question_words = {'who', 'what', 'where', 'when', 'why', 'how', 'which'}
        if word.lower() in question_words:
            return True
        
        return False
    
    def get_emphasis_segments(
        self, 
        analyses: List[WordAnalysis],
        min_cluster_size: int = 2
    ) -> List[Dict[str, any]]:
        """
        Find segments with high emphasis density
        
        Args:
            analyses: List of WordAnalysis objects
            min_cluster_size: Minimum words in cluster
            
        Returns:
            List of emphasis segments with start/end times
        """
        segments = []
        current_segment = None
        
        for analysis in analyses:
            if analysis.is_emphasis:
                if current_segment is None:
                    # Start new segment
                    current_segment = {
                        'start_s': analysis.start_s,
                        'end_s': analysis.end_s,
                        'words': [analysis.word],
                        'count': 1
                    }
                else:
                    # Extend segment
                    current_segment['end_s'] = analysis.end_s
                    current_segment['words'].append(analysis.word)
                    current_segment['count'] += 1
            else:
                # End of emphasis cluster
                if current_segment and current_segment['count'] >= min_cluster_size:
                    segments.append(current_segment)
                current_segment = None
        
        # Don't forget last segment
        if current_segment and current_segment['count'] >= min_cluster_size:
            segments.append(current_segment)
        
        return segments
    
    def get_cta_segments(self, analyses: List[WordAnalysis]) -> List[Dict[str, any]]:
        """Find CTA segments in transcript"""
        
        segments = []
        
        for i, analysis in enumerate(analyses):
            if analysis.is_cta_keyword:
                # Look for surrounding context
                start_idx = max(0, i - 5)
                end_idx = min(len(analyses), i + 5)
                
                segment = {
                    'start_s': analyses[start_idx].start_s,
                    'end_s': analyses[end_idx-1].end_s,
                    'cta_word': analysis.word,
                    'context': ' '.join([a.word for a in analyses[start_idx:end_idx]])
                }
                
                segments.append(segment)
        
        return segments
    
    def calculate_pacing_metrics(self, analyses: List[WordAnalysis]) -> Dict[str, float]:
        """
        Calculate speech pacing metrics
        
        Returns:
            Dict with WPM, avg_word_duration, pauses, etc.
        """
        if not analyses:
            return {}
        
        # Calculate words per minute
        total_duration = analyses[-1].end_s - analyses[0].start_s
        wpm = (len(analyses) / total_duration) * 60 if total_duration > 0 else 0
        
        # Calculate average word duration
        word_durations = [a.end_s - a.start_s for a in analyses]
        avg_word_duration = sum(word_durations) / len(word_durations)
        
        # Detect pauses (gaps > 0.5s between words)
        pauses = []
        for i in range(len(analyses) - 1):
            gap = analyses[i+1].start_s - analyses[i].end_s
            if gap > 0.5:
                pauses.append({
                    'time_s': analyses[i].end_s,
                    'duration_s': gap
                })
        
        return {
            'words_per_minute': round(wpm, 1),
            'avg_word_duration_s': round(avg_word_duration, 3),
            'pause_count': len(pauses),
            'pauses': pauses,
            'total_duration_s': round(total_duration, 2)
        }


# Example usage
if __name__ == "__main__":
    # Test with sample transcript
    sample_words = [
        {'word': 'Hey', 'start': 0.0, 'end': 0.3},
        {'word': 'struggling', 'start': 0.3, 'end': 0.8},
        {'word': 'with', 'start': 0.8, 'end': 1.0},
        {'word': 'Notion', 'start': 1.0, 'end': 1.4},
        {'word': '?', 'start': 1.4, 'end': 1.5},
        {'word': 'Here', 'start': 1.8, 'end': 2.0},
        {'word': 'is', 'start': 2.0, 'end': 2.1},
        {'word': 'how', 'start': 2.1, 'end': 2.3},
        {'word': 'to', 'start': 2.3, 'end': 2.4},
        {'word': 'fix', 'start': 2.4, 'end': 2.7},
        {'word': 'it', 'start': 2.7, 'end': 2.9},
    ]
    
    analyzer = WordAnalyzer()
    results = analyzer.analyze_transcript(sample_words)
    
    print("Word Analysis Results:")
    print("=" * 60)
    for r in results:
        print(f"{r.word_index:2d}. {r.word:12s} [{r.start_s:.1f}s-{r.end_s:.1f}s]")
        print(f"    Emphasis: {r.is_emphasis}, CTA: {r.is_cta_keyword}")
        print(f"    Function: {r.speech_function}, Sentiment: {r.sentiment_score}")
        print()
    
    print("\nPacing Metrics:")
    print("=" * 60)
    metrics = analyzer.calculate_pacing_metrics(results)
    for key, value in metrics.items():
        if key != 'pauses':
            print(f"{key}: {value}")
