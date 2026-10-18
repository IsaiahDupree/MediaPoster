"""
YTP-003: Transcript AI Analysis
Analyzes video transcripts using AI to extract key topics, summaries, and insights.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class TranscriptAnalysis:
    """AI analysis of a transcript."""
    video_id: str
    summary: str = ""
    key_topics: List[str] = field(default_factory=list)
    key_quotes: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    content_type: str = "educational"
    blog_outline: List[str] = field(default_factory=list)
    social_hooks: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    analyzed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TranscriptAnalyzer:
    """
    Analyzes transcripts using GPT-4o to extract insights.

    Generates:
    - Summaries (short and long)
    - Key topics and themes
    - Notable quotes
    - Blog post outlines
    - Social media hooks
    - Content classification
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def analyze(
        self,
        transcript_text: str,
        video_id: str = "",
        video_title: str = "",
    ) -> TranscriptAnalysis:
        """
        Analyze a transcript using AI.

        Args:
            transcript_text: Full transcript text
            video_id: Video identifier
            video_title: Video title for context

        Returns:
            TranscriptAnalysis with extracted insights
        """
        word_count = len(transcript_text.split())
        reading_time = max(1, word_count // 200)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            prompt = f"""Analyze this video transcript and provide:
1. A 2-3 sentence summary
2. 5-8 key topics/themes
3. 3-5 notable quotes
4. Sentiment (positive/negative/neutral/mixed)
5. Content type (educational/entertainment/news/opinion/tutorial)
6. A blog post outline (5-8 sections)
7. 3 social media hooks for promoting this content
8. 5-10 relevant hashtags

Video Title: {video_title}
Transcript:
{transcript_text[:8000]}

Respond in JSON format with keys: summary, key_topics, key_quotes, sentiment, content_type, blog_outline, social_hooks, hashtags"""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return TranscriptAnalysis(
                video_id=video_id,
                summary=result.get("summary", ""),
                key_topics=result.get("key_topics", []),
                key_quotes=result.get("key_quotes", []),
                sentiment=result.get("sentiment", "neutral"),
                content_type=result.get("content_type", "educational"),
                blog_outline=result.get("blog_outline", []),
                social_hooks=result.get("social_hooks", []),
                hashtags=result.get("hashtags", []),
                word_count=word_count,
                reading_time_minutes=reading_time,
            )

        except ImportError:
            logger.warning("openai package not available for transcript analysis")
            return TranscriptAnalysis(
                video_id=video_id,
                word_count=word_count,
                reading_time_minutes=reading_time,
            )
        except Exception as e:
            logger.error("Transcript analysis failed: %s", e)
            return TranscriptAnalysis(
                video_id=video_id,
                word_count=word_count,
                reading_time_minutes=reading_time,
            )

    async def generate_blog_post(
        self,
        analysis: TranscriptAnalysis,
        transcript_text: str,
    ) -> str:
        """
        Generate a full blog post from analysis and transcript.

        Args:
            analysis: TranscriptAnalysis from analyze()
            transcript_text: Full transcript

        Returns:
            Markdown blog post
        """
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            outline = "\n".join(f"- {s}" for s in analysis.blog_outline)
            prompt = f"""Write a comprehensive blog post based on this video transcript.

Summary: {analysis.summary}
Key Topics: {', '.join(analysis.key_topics)}
Outline:
{outline}

Transcript excerpt:
{transcript_text[:6000]}

Write in markdown format with headers, paragraphs, and key takeaways. Target 1000-1500 words."""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Blog generation failed: %s", e)
            return f"# {analysis.summary}\n\n*Blog generation failed: {e}*"
