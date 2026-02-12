import asyncio
import logging

from youtube_transcript_api import YouTubeTranscriptApi

from app.models.schemas import SubtitleResult, SubtitleSegment

logger = logging.getLogger(__name__)

_api = YouTubeTranscriptApi()


def _extract_sync(video_id: str, languages: list[str]) -> SubtitleResult | None:
    """Synchronous subtitle extraction."""
    try:
        transcript = _api.fetch(video_id, languages=languages)
        segments = [
            SubtitleSegment(
                text=snippet.text,
                start=snippet.start,
                duration=snippet.duration,
            )
            for snippet in transcript
        ]
        return SubtitleResult(
            video_id=video_id,
            language=transcript.language,
            is_generated=transcript.is_generated,
            segments=segments,
        )
    except Exception as e:
        logger.warning("No subtitles for %s: %s", video_id, e)
        return None


async def extract_subtitles(
    video_id: str, languages: list[str] | None = None
) -> SubtitleResult | None:
    """Async wrapper for subtitle extraction."""
    langs = languages or ["ko", "en"]
    return await asyncio.to_thread(_extract_sync, video_id, langs)
