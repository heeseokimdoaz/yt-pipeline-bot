import asyncio
import json
import logging
import os
import tempfile

import yt_dlp

from app.models.schemas import SubtitleResult, SubtitleSegment

logger = logging.getLogger(__name__)


def _extract_sync(video_id: str, languages: list[str]) -> SubtitleResult | None:
    """Extract subtitles using yt-dlp's built-in subtitle downloader.

    Uses yt-dlp download mode to properly handle YouTube's rate limiting
    and session management. Subtitles are saved to a temp directory then parsed.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")

        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": languages,
            "subtitlesformat": "json3",
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "outtmpl": outtmpl,
            "ignoreerrors": True,
            "retries": 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            logger.warning("yt-dlp failed for %s: %s", video_id, e)
            return None

        if info is None:
            logger.debug("yt-dlp returned None for %s (rate limited?)", video_id)
            return None

        manual_subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}

        # Priority: manual > auto, preferred languages first
        for lang in languages:
            if lang in manual_subs:
                result = _read_subtitle_file(
                    tmpdir, video_id, lang, is_generated=False
                )
                if result:
                    return result

        for lang in languages:
            if lang in auto_subs:
                result = _read_subtitle_file(
                    tmpdir, video_id, lang, is_generated=True
                )
                if result:
                    return result

        # Fallback: check any downloaded subtitle file
        for fname in sorted(os.listdir(tmpdir)):
            if fname.endswith(".json3"):
                parts = fname.rsplit(".", 2)
                if len(parts) >= 3:
                    lang = parts[-2]
                    is_gen = lang not in manual_subs
                    result = _parse_file(
                        os.path.join(tmpdir, fname), video_id, lang, is_gen
                    )
                    if result:
                        return result

    logger.info("No subtitles available for %s", video_id)
    return None


def _read_subtitle_file(
    tmpdir: str, video_id: str, lang: str, is_generated: bool
) -> SubtitleResult | None:
    """Read a downloaded subtitle json3 file."""
    filepath = os.path.join(tmpdir, f"{video_id}.{lang}.json3")
    if not os.path.exists(filepath):
        return None
    return _parse_file(filepath, video_id, lang, is_generated)


def _parse_file(
    filepath: str, video_id: str, lang: str, is_generated: bool
) -> SubtitleResult | None:
    """Parse a json3 subtitle file into SubtitleResult."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        segments = _parse_json3(data)
        if not segments:
            return None

        return SubtitleResult(
            video_id=video_id,
            language=lang,
            is_generated=is_generated,
            segments=segments,
        )
    except Exception as e:
        logger.debug("Failed to parse subtitle file %s: %s", filepath, e)
        return None


def _parse_json3(data: dict) -> list[SubtitleSegment]:
    """Parse YouTube json3 subtitle format into segments."""
    segments = []
    events = data.get("events", [])

    for event in events:
        segs = event.get("segs")
        if not segs:
            continue

        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)

        segments.append(
            SubtitleSegment(
                text=text,
                start=start_ms / 1000.0,
                duration=duration_ms / 1000.0,
            )
        )

    return segments


async def extract_subtitles(
    video_id: str, languages: list[str] | None = None
) -> SubtitleResult | None:
    """Async wrapper for subtitle extraction."""
    langs = languages or ["ko", "en"]
    return await asyncio.to_thread(_extract_sync, video_id, langs)
