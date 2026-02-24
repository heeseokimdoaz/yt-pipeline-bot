import asyncio
import json
import logging
import os
import random
import tempfile

import yt_dlp

from app.config import settings
from app.models.schemas import SubtitleResult, SubtitleSegment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Proxy pool — parsed once from comma-separated config
# ---------------------------------------------------------------------------
_proxy_pool: list[str] = []


def _get_proxy_pool() -> list[str]:
    global _proxy_pool
    if not _proxy_pool and settings.subtitle_proxies:
        _proxy_pool = [
            p.strip() for p in settings.subtitle_proxies.split(",") if p.strip()
        ]
        logger.info("Loaded %d proxies for subtitle extraction", len(_proxy_pool))
    return _proxy_pool


def _pick_proxy() -> str | None:
    pool = _get_proxy_pool()
    return random.choice(pool) if pool else None


# ---------------------------------------------------------------------------
# Core sync extraction (runs in thread pool)
# ---------------------------------------------------------------------------


def _extract_sync(video_id: str, languages: list[str]) -> SubtitleResult | None:
    """Extract subtitles using yt-dlp with configurable timeout and optional proxy."""
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
            "socket_timeout": settings.subtitle_socket_timeout,
            "outtmpl": outtmpl,
            "ignoreerrors": True,
            "retries": 5,
            "extractor_retries": 3,
        }

        proxy = _pick_proxy()
        if proxy:
            ydl_opts["proxy"] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            logger.warning(
                "yt-dlp failed for %s (proxy=%s): %s", video_id, proxy or "none", e
            )
            return None

        if info is None:
            logger.debug(
                "yt-dlp returned None for %s (rate limited?), proxy=%s",
                video_id,
                proxy or "none",
            )
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


# ---------------------------------------------------------------------------
# File reading / parsing helpers (unchanged logic)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Public async API — with retry + throttle
# ---------------------------------------------------------------------------


async def extract_subtitles(
    video_id: str, languages: list[str] | None = None
) -> SubtitleResult | None:
    """Extract subtitles with exponential-backoff retry and inter-request throttle.

    Retry logic:
        On failure, retries up to `subtitle_max_retries` times with exponential
        backoff (base_delay * 2^attempt + jitter).  Each retry may use a
        different proxy from the pool.

    Throttle:
        A random delay between `subtitle_throttle_min` and
        `subtitle_throttle_max` is applied *before* each attempt to spread
        requests and avoid rate-limit bursts.
    """
    langs = languages or ["ko", "en"]
    max_retries = settings.subtitle_max_retries
    base_delay = settings.subtitle_retry_base_delay

    for attempt in range(max_retries + 1):
        # Throttle: random delay before each request
        delay = random.uniform(
            settings.subtitle_throttle_min, settings.subtitle_throttle_max
        )
        await asyncio.sleep(delay)

        result = await asyncio.to_thread(_extract_sync, video_id, langs)
        if result is not None:
            if attempt > 0:
                logger.info(
                    "Subtitle extraction for %s succeeded on attempt %d",
                    video_id,
                    attempt + 1,
                )
            return result

        # If this was the last attempt, don't log retry
        if attempt < max_retries:
            backoff = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "Subtitle extraction failed for %s (attempt %d/%d), "
                "retrying in %.1fs...",
                video_id,
                attempt + 1,
                max_retries + 1,
                backoff,
            )
            await asyncio.sleep(backoff)

    logger.warning(
        "Subtitle extraction for %s failed after %d attempts",
        video_id,
        max_retries + 1,
    )
    return None
