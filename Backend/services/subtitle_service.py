"""
Auto-Subtitle Service
=====================
Transcribes videos with OpenAI Whisper and burns in styled captions
using FFmpeg. Integrates into the publish pipeline to automatically
add captions before uploading to social platforms.

Usage:
    service = AutoSubtitleService()
    result = await service.process_video(Path("video.mp4"), style="tiktok_bold")
    # result.output_path has the captioned video
"""

import os
import json
import hashlib
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field

from loguru import logger


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    text: str
    words: List[WordTiming]
    language: str = "en"
    duration: float = 0.0
    model: str = "whisper-1"


@dataclass
class SubtitleStyle:
    """FFmpeg ASS subtitle style configuration."""
    name: str
    font_name: str = "Arial-Bold"
    font_size: int = 58
    primary_color: str = "&H00FFFFFF"     # White (ASS BGR format)
    outline_color: str = "&H00000000"     # Black outline
    back_color: str = "&H80000000"        # Semi-transparent background
    bold: int = 1
    outline: int = 4
    shadow: int = 2
    alignment: int = 2                     # Bottom-center
    margin_v: int = 80                     # Vertical margin from bottom
    words_per_segment: int = 4


# ─── Style Presets ───────────────────────────────────────────────────────────

STYLE_PRESETS: Dict[str, SubtitleStyle] = {
    "tiktok_bold": SubtitleStyle(
        name="tiktok_bold",
        font_name="Avenir-Heavy",
        font_size=62,
        primary_color="&H00FFFFFF",
        outline_color="&H00000000",
        back_color="&H00000000",
        bold=1,
        outline=5,
        shadow=2,
        alignment=2,
        margin_v=350,       # ~center-ish for vertical video
        words_per_segment=4,
    ),
    "minimal_white": SubtitleStyle(
        name="minimal_white",
        font_name="Avenir-Medium",
        font_size=48,
        primary_color="&H00FFFFFF",
        outline_color="&H00000000",
        back_color="&H00000000",
        bold=0,
        outline=2,
        shadow=0,
        alignment=2,
        margin_v=100,
        words_per_segment=5,
    ),
    "bold_yellow": SubtitleStyle(
        name="bold_yellow",
        font_name="Avenir-Heavy",
        font_size=64,
        primary_color="&H0000FFFF",       # Yellow in ASS BGR
        outline_color="&H00000000",
        back_color="&H00000000",
        bold=1,
        outline=5,
        shadow=3,
        alignment=2,
        margin_v=350,
        words_per_segment=3,
    ),
    "boxed": SubtitleStyle(
        name="boxed",
        font_name="Avenir-Heavy",
        font_size=52,
        primary_color="&H00FFFFFF",
        outline_color="&H00000000",
        back_color="&H80000000",           # Semi-transparent box
        bold=1,
        outline=0,
        shadow=0,
        alignment=2,
        margin_v=350,
        words_per_segment=4,
    ),
    "none": SubtitleStyle(
        name="none",
        font_size=0,
    ),
}


@dataclass
class ProcessResult:
    success: bool
    output_path: Optional[Path] = None
    transcription: Optional[TranscriptionResult] = None
    srt_content: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


# ─── Main Service ────────────────────────────────────────────────────────────

class AutoSubtitleService:
    """
    End-to-end auto-subtitle pipeline:
    1. Transcribe with OpenAI Whisper API (word-level timestamps)
    2. Generate ASS subtitle file with style presets
    3. Burn into video with FFmpeg (near-lossless quality)
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("[Subtitles] OPENAI_API_KEY not set — transcription will fail")

    # ── Public API ───────────────────────────────────────────────────────

    async def process_video(
        self,
        video_path: Path,
        style: str = "tiktok_bold",
        output_path: Optional[Path] = None,
    ) -> ProcessResult:
        """
        Full pipeline: transcribe → generate subtitles → burn into video.

        Args:
            video_path: Path to the input video file
            style: One of STYLE_PRESETS keys ("tiktok_bold", "minimal_white", etc.)
            output_path: Custom output path. Default: {name}_captioned.mp4

        Returns:
            ProcessResult with output_path and transcription data
        """
        if style == "none":
            return ProcessResult(
                success=True,
                output_path=video_path,
                skipped=True,
                skip_reason="Caption style is 'none'",
            )

        if not video_path.exists():
            return ProcessResult(success=False, error=f"Video not found: {video_path}")

        style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["tiktok_bold"])
        logger.info(f"[Subtitles] Processing {video_path.name} with style={style}")

        # Step 1: Transcribe
        transcription = await self.transcribe(video_path)
        if not transcription:
            return ProcessResult(success=False, error="Transcription failed")

        if not transcription.words:
            return ProcessResult(
                success=True,
                output_path=video_path,
                transcription=transcription,
                skipped=True,
                skip_reason="No words detected in audio",
            )

        logger.info(
            f"[Subtitles] Transcribed: {len(transcription.words)} words, "
            f"{transcription.duration:.1f}s, lang={transcription.language}"
        )

        # Step 2: Generate ASS subtitle file
        video_w, video_h = self._get_video_dimensions(video_path)
        segments = self._group_words(transcription.words, style_config.words_per_segment)
        ass_content = self._generate_ass(segments, style_config, video_w, video_h)
        srt_content = self._generate_srt(segments)

        # Step 3: Burn into video with FFmpeg
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_captioned{video_path.suffix}"

        success = await self._burn_subtitles(video_path, ass_content, output_path)

        if success:
            logger.success(f"[Subtitles] ✓ Captioned video: {output_path.name}")
            return ProcessResult(
                success=True,
                output_path=output_path,
                transcription=transcription,
                srt_content=srt_content,
            )
        else:
            return ProcessResult(success=False, error="FFmpeg burn-in failed")

    # ── Transcription ────────────────────────────────────────────────────

    async def transcribe(self, video_path: Path) -> Optional[TranscriptionResult]:
        """Transcribe video audio using OpenAI Whisper API with word-level timestamps."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Extract audio first if video is large (Whisper API limit: 25MB)
            audio_path = await self._extract_audio_if_needed(video_path)
            file_to_send = audio_path or video_path

            file_size_mb = file_to_send.stat().st_size / (1024 * 1024)
            logger.info(f"[Subtitles] Sending {file_to_send.name} ({file_size_mb:.1f}MB) to Whisper API")

            with open(file_to_send, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )

            # Clean up temp audio file
            if audio_path and audio_path != video_path:
                try:
                    audio_path.unlink()
                except Exception:
                    pass

            # Parse response
            words = []
            if hasattr(response, "words") and response.words:
                for w in response.words:
                    words.append(WordTiming(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end,
                        confidence=getattr(w, "confidence", 1.0),
                    ))

            return TranscriptionResult(
                text=response.text,
                words=words,
                language=getattr(response, "language", "en"),
                duration=getattr(response, "duration", 0.0),
                model="whisper-1",
            )

        except Exception as e:
            logger.error(f"[Subtitles] Whisper transcription failed: {e}")
            return None

    async def _extract_audio_if_needed(self, video_path: Path) -> Optional[Path]:
        """Extract audio to a smaller file if video exceeds 25MB Whisper limit."""
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        if file_size_mb <= 24:
            return None  # Send video directly

        logger.info(f"[Subtitles] Video {file_size_mb:.0f}MB > 25MB limit, extracting audio...")
        audio_path = video_path.parent / f"{video_path.stem}_audio.mp3"

        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(video_path),
                "-vn", "-acodec", "libmp3lame", "-ab", "64k", "-ar", "16000",
                str(audio_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and audio_path.exists():
                logger.info(f"[Subtitles] Extracted audio: {audio_path.stat().st_size / (1024*1024):.1f}MB")
                return audio_path
            else:
                logger.error(f"[Subtitles] Audio extraction failed: {result.stderr[:200]}")
                return None
        except Exception as e:
            logger.error(f"[Subtitles] Audio extraction error: {e}")
            return None

    # ── Subtitle Generation ──────────────────────────────────────────────

    def _group_words(
        self, words: List[WordTiming], words_per_segment: int = 4
    ) -> List[Dict]:
        """Group word timings into subtitle segments of N words."""
        segments = []
        for i in range(0, len(words), words_per_segment):
            group = words[i : i + words_per_segment]
            if group:
                segments.append({
                    "text": " ".join(w.word for w in group),
                    "start": group[0].start,
                    "end": group[-1].end,
                })
        return segments

    def _generate_ass(
        self,
        segments: List[Dict],
        style: SubtitleStyle,
        video_w: int = 1080,
        video_h: int = 1920,
    ) -> str:
        """Generate ASS subtitle content with style configuration."""
        # Border style: 1 = outline+shadow, 3 = opaque box
        border_style = 3 if style.back_color != "&H00000000" else 1

        header = f"""[Script Info]
Title: AutoSubtitles
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{style.primary_color},&H000000FF,{style.outline_color},{style.back_color},{style.bold},0,0,0,100,100,0,0,{border_style},{style.outline},{style.shadow},{style.alignment},20,20,{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [header.strip()]
        for seg in segments:
            start = self._ass_timestamp(seg["start"])
            end = self._ass_timestamp(seg["end"])
            text = seg["text"].replace("\n", "\\N")
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        return "\n".join(lines)

    def _generate_srt(self, segments: List[Dict]) -> str:
        """Generate SRT subtitle content (for storage/reference)."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._srt_timestamp(seg["start"])
            end = self._srt_timestamp(seg["end"])
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")
        return "\n".join(lines)

    # ── FFmpeg Burn-in ───────────────────────────────────────────────────

    async def _burn_subtitles(
        self, video_path: Path, ass_content: str, output_path: Path
    ) -> bool:
        """Burn ASS subtitles into video using FFmpeg."""
        # Write ASS to temp file
        ass_path = video_path.parent / f"{video_path.stem}_subs.ass"
        try:
            ass_path.write_text(ass_content, encoding="utf-8")

            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"ass='{ass_path}'",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",            # Near-lossless quality
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(output_path),
            ]

            logger.info(f"[Subtitles] Burning captions with FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and output_path.exists():
                # Verify output is reasonable size
                in_size = video_path.stat().st_size
                out_size = output_path.stat().st_size
                ratio = out_size / in_size if in_size > 0 else 0
                logger.info(
                    f"[Subtitles] FFmpeg done: {in_size/(1024*1024):.1f}MB → "
                    f"{out_size/(1024*1024):.1f}MB ({ratio:.1%})"
                )
                return True
            else:
                logger.error(f"[Subtitles] FFmpeg failed: {result.stderr[-500:]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("[Subtitles] FFmpeg timed out (>300s)")
            return False
        except Exception as e:
            logger.error(f"[Subtitles] FFmpeg error: {e}")
            return False
        finally:
            # Cleanup temp ASS file
            try:
                ass_path.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_video_dimensions(self, video_path: Path) -> Tuple[int, int]:
        """Get video width×height via ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                str(video_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                return int(parts[0]), int(parts[1])
        except Exception as e:
            logger.warning(f"[Subtitles] Could not probe dimensions: {e}")
        return 1080, 1920  # Default: vertical video

    @staticmethod
    def _ass_timestamp(seconds: float) -> str:
        """Format seconds → ASS timestamp H:MM:SS.cc"""
        if seconds < 0:
            seconds = 0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    @staticmethod
    def _srt_timestamp(seconds: float) -> str:
        """Format seconds → SRT timestamp HH:MM:SS,mmm"""
        if seconds < 0:
            seconds = 0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def get_available_styles() -> Dict[str, str]:
        """Return available style presets with descriptions."""
        return {
            "tiktok_bold": "White bold text, heavy outline, centered — best for TikTok/Reels",
            "minimal_white": "Clean white text, bottom-aligned — best for YouTube Shorts",
            "bold_yellow": "Yellow bold text, heavy outline — high contrast, attention-grabbing",
            "boxed": "White text on semi-transparent black box — maximum readability",
            "none": "No captions — skip subtitle processing",
        }
