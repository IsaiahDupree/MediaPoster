"""
Transcript Extraction with Word-Level Timestamps
Uses OpenAI Whisper API for accurate transcription
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger
import os

try:
    from openai import OpenAI
except ImportError:
    logger.warning("openai not installed. Run: pip install openai")


@dataclass
class Word:
    """Single word with timestamp"""
    word: str
    start: float
    end: float
    index: int


@dataclass
class Sentence:
    """Grouped words forming a sentence"""
    text: str
    words: List[Word]
    start: float
    end: float
    sentence_id: int


@dataclass
class TranscriptResult:
    """Complete transcript with metadata"""
    text: str
    words: List[Word]
    sentences: List[Sentence]
    duration: float
    language: str


class TranscriptExtractor:
    """Extract word-level transcripts from video"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with OpenAI API key
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.error("OpenAI API key not found")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("Transcript Extractor initialized")
    
    def extract_with_timestamps(self, video_path: str) -> Optional[TranscriptResult]:
        """
        Extract transcript with word-level timestamps
        
        Args:
            video_path: Path to video file
            
        Returns:
            TranscriptResult with words and sentences
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
        
        logger.info(f"Extracting transcript from {video_path}")
        
        try:
            # Open video file
            with open(video_path, 'rb') as video_file:
                # Call Whisper API with word timestamps
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=video_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            # Extract word-level data
            words = []
            
            if hasattr(transcript, 'words') and transcript.words:
                for idx, word_data in enumerate(transcript.words):
                    word = Word(
                        word=word_data.word.strip(),
                        start=word_data.start,
                        end=word_data.end,
                        index=idx
                    )
                    words.append(word)
            
            # Segment into sentences
            sentences = self.segment_sentences(words)
            
            result = TranscriptResult(
                text=transcript.text,
                words=words,
                sentences=sentences,
                duration=words[-1].end if words else 0.0,
                language=getattr(transcript, 'language', 'en')
            )
            
            logger.success(f"Extracted {len(words)} words, {len(sentences)} sentences")
            return result
            
        except Exception as e:
            logger.error(f"Transcript extraction failed: {e}")
            return None
    
    def segment_sentences(self, words: List[Word]) -> List[Sentence]:
        """
        Group words into sentences
        
        Args:
            words: List of words with timestamps
            
        Returns:
            List of sentences
        """
        if not words:
            return []
        
        sentences = []
        current_words = []
        sentence_id = 0
        
        # Simple sentence boundary detection (punctuation + pause)
        for i, word in enumerate(words):
            current_words.append(word)
            
            # Check for sentence end
            is_end_punctuation = word.word.rstrip().endswith(('.', '!', '?'))
            
            # Check for significant pause (> 0.5s to next word)
            is_pause = False
            if i < len(words) - 1:
                pause = words[i + 1].start - word.end
                is_pause = pause > 0.5
            
            # End sentence if punctuation or pause, or last word
            if is_end_punctuation or is_pause or i == len(words) - 1:
                if current_words:
                    sentence = Sentence(
                        text=' '.join(w.word for w in current_words),
                        words=current_words.copy(),
                        start=current_words[0].start,
                        end=current_words[-1].end,
                        sentence_id=sentence_id
                    )
                    sentences.append(sentence)
                    current_words = []
                    sentence_id += 1
        
        return sentences
    
    def analyze_pacing(self, words: List[Word], window_seconds: float = 5.0) -> List[Dict[str, Any]]:
        """
        Analyze speaking pace (words per minute) over time
        
        Args:
            words: List of words
            window_seconds: Sliding window size
            
        Returns:
            List of {start_s, end_s, wpm}
        """
        if not words:
            return []
        
        pacing = []
        duration = words[-1].end
        
        # Sliding window
        for t in range(0, int(duration), int(window_seconds / 2)):  # 50% overlap
            window_start = t
            window_end = t + window_seconds
            
            # Count words in window
            window_words = [
                w for w in words 
                if window_start <= w.start < window_end
            ]
            
            if window_words:
                wpm = (len(window_words) / window_seconds) * 60
                pacing.append({
                    'start_s': window_start,
                    'end_s': window_end,
                    'wpm': wpm,
                    'word_count': len(window_words)
                })
        
        return pacing
    
    def detect_emphasis_words(self, words: List[Word]) -> List[Word]:
        """
        Detect words likely to be emphasized
        
        Args:
            words: List of words
            
        Returns:
            List of emphasis words
        """
        emphasis_words = []
        
        # Keywords that are often emphasized
        emphasis_keywords = {
            'never', 'always', 'stop', 'start', 'now', 'today',
            'secret', 'mistake', 'wrong', 'right', 'must', 'need',
            'important', 'critical', 'key', 'exactly', 'only'
        }
        
        for word in words:
            word_lower = word.word.lower().strip('.,!?')
            
            # Check if it's an emphasis keyword
            if word_lower in emphasis_keywords:
                emphasis_words.append(word)
            # Check if it's all caps (excluding single letters)
            elif len(word.word) > 1 and word.word.isupper():
                emphasis_words.append(word)
            # Check if it's a number
            elif word.word.strip('.,!?').isdigit():
                emphasis_words.append(word)
        
        return emphasis_words
    
    def detect_questions(self, sentences: List[Sentence]) -> List[Sentence]:
        """Detect question sentences"""
        questions = []
        
        question_words = {'what', 'why', 'how', 'when', 'where', 'who', 'which'}
        
        for sentence in sentences:
            # Check for question mark
            if sentence.text.strip().endswith('?'):
                questions.append(sentence)
            # Check for question word at start
            elif sentence.words and sentence.words[0].word.lower() in question_words:
                questions.append(sentence)
        
        return questions


# Example usage
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    extractor = TranscriptExtractor()
    
    # Test with a video file
    test_video = "test_video.mp4"
    
    if os.path.exists(test_video):
        logger.info(f"Testing transcript extraction on {test_video}")
        
        result = extractor.extract_with_timestamps(test_video)
        
        if result:
            logger.info(f"\nFull Transcript:")
            logger.info(f"{result.text}\n")
            
            logger.info(f"Duration: {result.duration:.2f}s")
            logger.info(f"Words: {len(result.words)}")
            logger.info(f"Sentences: {len(result.sentences)}\n")
            
            # Show first few words
            logger.info("First 10 words:")
            for word in result.words[:10]:
                logger.info(f"  {word.start:.2f}-{word.end:.2f}s: {word.word}")
            
            # Pacing analysis
            pacing = extractor.analyze_pacing(result.words)
            logger.info(f"\nPacing analysis ({len(pacing)} windows):")
            for p in pacing[:3]:
                logger.info(f"  {p['start_s']}-{p['end_s']}s: {p['wpm']:.0f} WPM")
            
            # Emphasis words
            emphasis = extractor.detect_emphasis_words(result.words)
            logger.info(f"\nEmphasis words ({len(emphasis)}):")
            for word in emphasis[:5]:
                logger.info(f"  {word.start:.2f}s: {word.word}")
            
            # Questions
            questions = extractor.detect_questions(result.sentences)
            logger.info(f"\nQuestions ({len(questions)}):")
            for q in questions[:3]:
                logger.info(f"  {q.start:.2f}s: {q.text}")
    else:
        logger.warning(f"Test video not found: {test_video}")
        logger.info("Create a test video or specify an existing one")
