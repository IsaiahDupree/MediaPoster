"""
Transcript Scanner
Analyzes transcripts to identify highlight-worthy content
"""
from typing import List, Dict, Optional, Set
from loguru import logger
import re


class TranscriptScanner:
    """Scan transcripts for highlight indicators"""
    
    # Patterns that indicate interesting moments
    HOOK_PATTERNS = [
        r'\b(watch|check|look at?|see) this\b',
        r'\b(you (?:won\'t|wont) believe)\b',
        r'\b(the (?:craziest|wildest|funniest))\b',
        r'\b(wait for it)\b',
        r'\b(here\'s what happened)\b',
        r'\b(let me (?:show|tell) you)\b',
    ]
    
    EMPHASIS_WORDS = {
        'amazing', 'incredible', 'unbelievable', 'crazy', 'insane',
        'awesome', 'fantastic', 'wow', 'omg', 'seriously',
        'literally', 'actually', 'honestly', 'really', 'extremely'
    }
    
    QUESTION_WORDS = {
        'what', 'how', 'why', 'when', 'where', 'who',
        'which', 'whose', 'whom'
    }
    
    STORY_TRANSITIONS = {
        'so', 'then', 'suddenly', 'all of a sudden', 'and then',
        'but', 'however', 'meanwhile', 'after that', 'next'
    }
    
    def __init__(self):
        """Initialize transcript scanner"""
        self.hook_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.HOOK_PATTERNS]
        logger.info("Transcript scanner initialized")
    
    def scan_for_hooks(self, transcript: Dict) -> List[Dict]:
        """
        Find hook phrases (attention-grabbing moments)
        
        Args:
            transcript: Whisper transcript with segments
            
        Returns:
            List of hook moments with timestamps
        """
        logger.info("Scanning transcript for hooks")
        
        if 'segments' not in transcript:
            return []
        
        hooks = []
        
        for segment in transcript['segments']:
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            # Check against hook patterns
            for pattern in self.hook_regexes:
                if pattern.search(text):
                    hooks.append({
                        'timestamp': start,
                        'duration': end - start,
                        'text': text,
                        'type': 'hook_phrase',
                        'pattern': pattern.pattern,
                        'score': 1.0
                    })
                    break  # One hook per segment
        
        logger.success(f"✓ Found {len(hooks)} hook phrases")
        return hooks
    
    def scan_for_questions(self, transcript: Dict) -> List[Dict]:
        """
        Find questions (engaging moments)
        
        Args:
            transcript: Whisper transcript with segments
            
        Returns:
            Questions with timestamps
        """
        logger.info("Scanning transcript for questions")
        
        if 'segments' not in transcript:
            return []
        
        questions = []
        
        for segment in transcript['segments']:
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            # Check if segment contains a question
            if '?' in text:
                questions.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': text,
                    'type': 'question',
                    'score': 0.8
                })
            elif any(text.lower().startswith(qw) for qw in self.QUESTION_WORDS):
                # Question without punctuation
                questions.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': text,
                    'type': 'question',
                    'score': 0.7
                })
        
        logger.success(f"✓ Found {len(questions)} questions")
        return questions
    
    def scan_for_punchlines(self, transcript: Dict) -> List[Dict]:
        """
        Identify potential punchlines (humor peaks)
        
        Args:
            transcript: Whisper transcript with segments
            
        Returns:
            Potential punchlines
        """
        logger.info("Scanning for punchlines")
        
        if 'segments' not in transcript:
            return []
        
        punchlines = []
        
        for i, segment in enumerate(transcript['segments']):
            text = segment.get('text', '').strip().lower()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            # Indicators of punchlines:
            # 1. Short segment after longer setup
            # 2. Contains laughter indicators (haha, lol)
            # 3. Ends with exclamation
            
            is_short = (end - start) < 3.0
            has_laughter = any(word in text for word in ['haha', 'lol', 'hehe'])
            has_exclamation = '!' in segment.get('text', '')
            
            # Check if previous segment was longer (setup)
            has_setup = False
            if i > 0:
                prev_segment = transcript['segments'][i-1]
                prev_duration = prev_segment.get('end', 0) - prev_segment.get('start', 0)
                if prev_duration > (end - start) * 1.5:
                    has_setup = True
            
            # Score based on indicators
            score = 0.0
            if is_short and has_setup:
                score += 0.4
            if has_laughter:
                score += 0.3
            if has_exclamation:
                score += 0.2
            
            if score >= 0.5:
                punchlines.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': segment.get('text', ''),
                    'type': 'punchline',
                    'score': score,
                    'indicators': {
                        'short': is_short,
                        'has_setup': has_setup,
                        'laughter': has_laughter,
                        'exclamation': has_exclamation
                    }
                })
        
        logger.success(f"✓ Found {len(punchlines)} potential punchlines")
        return punchlines
    
    def scan_for_emphasis(self, transcript: Dict) -> List[Dict]:
        """
        Find emphasized speech (strong words)
        
        Args:
            transcript: Whisper transcript with segments
            
        Returns:
            Emphasized moments
        """
        logger.info("Scanning for emphasis")
        
        if 'segments' not in transcript:
            return []
        
        emphasized = []
        
        for segment in transcript['segments']:
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            words = set(re.findall(r'\b\w+\b', text.lower()))
            emphasis_found = words & self.EMPHASIS_WORDS
            
            if emphasis_found:
                # Score based on number and strength of emphasis words
                score = min(len(emphasis_found) * 0.3, 1.0)
                
                emphasized.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': text,
                    'type': 'emphasis',
                    'emphasis_words': list(emphasis_found),
                    'score': score
                })
        
        logger.success(f"✓ Found {len(emphasized)} emphasized segments")
        return emphasized
    
    def scan_for_story_beats(self, transcript: Dict) -> List[Dict]:
        """
        Identify story progression beats
        
        Args:
            transcript: Whisper transcript with segments
            
        Returns:
            Story beat moments
        """
        logger.info("Scanning for story beats")
        
        if 'segments' not in transcript:
            return []
        
        beats = []
        
        for segment in transcript['segments']:
            text = segment.get('text', '').strip().lower()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            # Check for transition words at start
            words = text.split()
            if words and any(words[0].startswith(trans) for trans in self.STORY_TRANSITIONS):
                beats.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': segment.get('text', ''),
                    'type': 'story_beat',
                    'transition': words[0],
                    'score': 0.6
                })
        
        logger.success(f"✓ Found {len(beats)} story beats")
        return beats
    
    def extract_key_phrases(
        self,
        transcript: Dict,
        min_words: int = 3,
        max_phrases: int = 20
    ) -> List[Dict]:
        """
        Extract key phrases from transcript
        
        Args:
            transcript: Whisper transcript
            min_words: Minimum words in phrase
            max_phrases: Maximum phrases to return
            
        Returns:
            Key phrases with timestamps
        """
        logger.info("Extracting key phrases")
        
        if 'segments' not in transcript:
            return []
        
        # Simple approach: look for segments with high word density
        # and emphasis markers
        
        phrases = []
        
        for segment in transcript['segments']:
            text = segment.get('text', '').strip()
            words = text.split()
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            if len(words) >= min_words:
                # Score based on various factors
                score = 0.0
                
                # Uppercase words (emphasis)
                uppercase_count = sum(1 for w in words if w.isupper() and len(w) > 1)
                score += min(uppercase_count * 0.2, 0.4)
                
                # Contains emphasis words
                emphasis_count = sum(1 for w in words if w.lower() in self.EMPHASIS_WORDS)
                score += min(emphasis_count * 0.2, 0.4)
                
                # Shorter, punchier phrases
                if len(words) <= 8:
                    score += 0.2
                
                phrases.append({
                    'timestamp': start,
                    'duration': end - start,
                    'text': text,
                    'word_count': len(words),
                    'score': score
                })
        
        # Sort by score and return top phrases
        phrases.sort(key=lambda x: x['score'], reverse=True)
        
        logger.success(f"✓ Extracted {len(phrases[:max_phrases])} key phrases")
        return phrases[:max_phrases]
    
    def scan_comprehensive(self, transcript: Dict) -> Dict:
        """
        Run all scans and return comprehensive results
        
        Args:
            transcript: Whisper transcript
            
        Returns:
            All scan results
        """
        logger.info("Running comprehensive transcript scan")
        
        results = {
            'hooks': self.scan_for_hooks(transcript),
            'questions': self.scan_for_questions(transcript),
            'punchlines': self.scan_for_punchlines(transcript),
            'emphasis': self.scan_for_emphasis(transcript),
            'story_beats': self.scan_for_story_beats(transcript),
            'key_phrases': self.extract_key_phrases(transcript)
        }
        
        # Count total highlights found
        total = sum(len(v) for v in results.values())
        logger.success(f"✓ Comprehensive scan complete: {total} highlights found")
        
        return results
    
    def score_timestamp_by_transcript(
        self,
        timestamp: float,
        transcript_highlights: Dict,
        window: float = 3.0
    ) -> float:
        """
        Score a timestamp based on transcript analysis
        
        Args:
            timestamp: Timestamp to score
            transcript_highlights: Results from scan_comprehensive
            window: Time window for proximity (seconds)
            
        Returns:
            Score (0-1)
        """
        score = 0.0
        
        # Check each highlight type
        for highlight_type, highlights in transcript_highlights.items():
            for highlight in highlights:
                h_ts = highlight['timestamp']
                distance = abs(timestamp - h_ts)
                
                if distance <= window:
                    # Proximity score
                    proximity = 1.0 - (distance / window)
                    
                    # Weight by highlight type
                    weight = {
                        'hooks': 0.3,
                        'punchlines': 0.25,
                        'questions': 0.15,
                        'emphasis': 0.15,
                        'story_beats': 0.1,
                        'key_phrases': 0.05
                    }.get(highlight_type, 0.1)
                    
                    # Add weighted score
                    highlight_score = highlight.get('score', 0.5)
                    score += proximity * weight * highlight_score
        
        return min(score, 1.0)


# Example usage and testing
if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python transcript_scanner.py <transcript_json>")
        print("   or: python transcript_scanner.py <video_file>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    
    # Check if it's a transcript JSON or video file
    if input_path.suffix == '.json':
        with open(input_path) as f:
            transcript = json.load(f)
    else:
        print("For video files, first run whisper to get transcript")
        print("Example: python -m modules.ai_analysis.whisper_service video.mp4")
        sys.exit(1)
    
    # Test transcript scanning
    scanner = TranscriptScanner()
    
    print("\n" + "="*60)
    print("TRANSCRIPT ANALYSIS")
    print("="*60)
    
    # Run comprehensive scan
    results = scanner.scan_comprehensive(transcript)
    
    # Display results
    for highlight_type, highlights in results.items():
        if highlights:
            print(f"\n{highlight_type.upper()}: {len(highlights)} found")
            for i, h in enumerate(highlights[:3]):
                print(f"  {i+1}. [{h['timestamp']:.1f}s] {h['text'][:60]}...")
                if 'score' in h:
                    print(f"      Score: {h['score']:.2f}")
