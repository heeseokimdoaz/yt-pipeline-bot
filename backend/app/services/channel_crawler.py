import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from googleapiclient.discovery import build

from app.config import settings
from app.models.channel_schemas import ChannelConfig
from app.models.schemas import VideoData
from app.services.vector_store import get_existing_video_ids
from app.utils.quota_tracker import quota_tracker

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHANNELS_JSON = DATA_DIR / "channels.json"
CHANNELS_CSV = DATA_DIR / "channels.csv"

_channels_cache: list[ChannelConfig] | None = None


def _build_youtube():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


# --- Channel config ---


def load_channels(force_reload: bool = False) -> list[ChannelConfig]:
    """Load channel configs from channels.json with caching."""
    global _channels_cache
    if _channels_cache is not None and not force_reload:
        return _channels_cache

    if not CHANNELS_JSON.exists():
        _channels_cache = []
        return _channels_cache

    with open(CHANNELS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    _channels_cache = [ChannelConfig(**ch) for ch in data]
    return _channels_cache


def _save_channels(channels: list[ChannelConfig]) -> None:
    """Save channel configs to channels.json and refresh cache."""
    global _channels_cache
    data = [ch.model_dump() for ch in channels]
    with open(CHANNELS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _channels_cache = channels


def get_enabled_channels() -> list[ChannelConfig]:
    """Return only enabled channels with resolved channel IDs."""
    return [
        ch for ch in load_channels()
        if ch.enabled and ch.channel_id and ch.uploads_playlist_id
    ]


# --- CSV Sync ---


def _extract_handle(url: str) -> str:
    """Extract @handle from YouTube URL."""
    path = urlparse(url.strip()).path.rstrip("/")
    # https://www.youtube.com/@handle → @handle
    if "/@" in path:
        return "@" + path.split("/@")[-1]
    return ""


def sync_channels_from_csv() -> dict:
    """Sync channels.json with channels.csv.

    CSV is the source of truth for which channels to include.
    channels.json is a cache for resolved channel_id / uploads_playlist_id.

    Returns summary of changes.
    """
    if not CHANNELS_CSV.exists():
        logger.warning("channels.csv not found at %s", CHANNELS_CSV)
        return {"error": "channels.csv not found"}

    # Read CSV
    csv_channels: list[dict] = []
    with open(CHANNELS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("채널명", "").strip()
            if not name:
                continue
            handle = _extract_handle(row.get("유튜브 주소", ""))
            csv_channels.append({
                "channel_name": name,
                "handle": handle,
                "category": row.get("Unnamed: 0", "중립/종합").strip(),
                "description": row.get("주요 특징", "").strip(),
            })

    # Read existing cache for resolved IDs
    existing = load_channels(force_reload=True)
    cache_by_handle: dict[str, ChannelConfig] = {}
    cache_by_name: dict[str, ChannelConfig] = {}
    for ch in existing:
        if ch.handle:
            cache_by_handle[ch.handle.lower()] = ch
        cache_by_name[ch.channel_name] = ch

    # Build new channel list from CSV, reusing cached IDs
    new_channels: list[ChannelConfig] = []
    added = 0
    removed_names: list[str] = []
    unresolved: list[str] = []

    csv_handles = set()
    csv_names = set()

    for row in csv_channels:
        handle = row["handle"]
        name = row["channel_name"]
        csv_handles.add(handle.lower())
        csv_names.add(name)

        # Try to find cached data
        cached = cache_by_handle.get(handle.lower()) or cache_by_name.get(name)

        if cached and cached.channel_id:
            # Reuse resolved ID, update description/category from CSV
            new_channels.append(ChannelConfig(
                channel_id=cached.channel_id,
                channel_name=name,
                handle=handle,
                uploads_playlist_id=cached.uploads_playlist_id,
                category=row["category"],
                description=row["description"],
                enabled=True,
            ))
        else:
            # New channel, needs resolution
            new_channels.append(ChannelConfig(
                channel_name=name,
                handle=handle,
                category=row["category"],
                description=row["description"],
                enabled=True,
            ))
            unresolved.append(name)
            added += 1

    # Find removed channels
    for ch in existing:
        handle_match = ch.handle and ch.handle.lower() in csv_handles
        name_match = ch.channel_name in csv_names
        if not handle_match and not name_match:
            removed_names.append(ch.channel_name)

    # Resolve unresolved channels via YouTube API
    resolved_count = 0
    if unresolved:
        resolved_count = _resolve_unresolved(new_channels)

    _save_channels(new_channels)

    result = {
        "total": len(new_channels),
        "added": added,
        "removed": removed_names,
        "resolved": resolved_count,
        "unresolved": [ch.channel_name for ch in new_channels if not ch.channel_id],
    }
    logger.info("CSV sync: %s", result)
    return result


def _resolve_unresolved(channels: list[ChannelConfig]) -> int:
    """Resolve channel_id for channels missing it. Returns count of resolved."""
    youtube = _build_youtube()
    resolved = 0

    for ch in channels:
        if ch.channel_id:
            continue

        # Try handle-based resolution first (1 quota unit)
        if ch.handle:
            handle_clean = ch.handle.lstrip("@")
            try:
                if quota_tracker.consume(1):
                    resp = youtube.channels().list(
                        part="id", forHandle=handle_clean
                    ).execute()
                    items = resp.get("items", [])
                    if items:
                        ch.channel_id = items[0]["id"]
                        ch.uploads_playlist_id = "UU" + ch.channel_id[2:]
                        resolved += 1
                        logger.info("Resolved %s → %s", ch.channel_name, ch.channel_id)
                        continue
            except Exception as e:
                logger.warning("Handle resolution failed for %s: %s", ch.channel_name, e)

        # Fallback: search by name (100 quota units)
        try:
            if quota_tracker.consume(100):
                resp = youtube.search().list(
                    part="snippet", q=ch.channel_name, type="channel", maxResults=1
                ).execute()
                items = resp.get("items", [])
                if items:
                    ch.channel_id = items[0]["snippet"]["channelId"]
                    ch.uploads_playlist_id = "UU" + ch.channel_id[2:]
                    resolved += 1
                    logger.info("Resolved (search) %s → %s", ch.channel_name, ch.channel_id)
        except Exception as e:
            logger.warning("Search resolution failed for %s: %s", ch.channel_name, e)

    return resolved


# --- YouTube API calls ---


def _fetch_recent_uploads_sync(
    playlist_id: str, days: int = 7
) -> list[str]:
    """Fetch video IDs from an uploads playlist published within `days` days.

    Returns list of video_ids. Costs 1 quota unit per page.
    """
    youtube = _build_youtube()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    video_ids: list[str] = []
    page_token = None

    for _ in range(5):  # max 5 pages (250 videos)
        if not quota_tracker.consume(1):
            logger.warning("Quota exhausted during playlist fetch")
            break

        params = dict(
            playlistId=playlist_id,
            part="contentDetails",
            maxResults=50,
            pageToken=page_token,
        )
        response = youtube.playlistItems().list(**{k: v for k, v in params.items() if v is not None}).execute()

        stop = False
        for item in response.get("items", []):
            published_str = item["contentDetails"].get("videoPublishedAt", "")
            if not published_str:
                continue
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            if published < cutoff:
                stop = True
                break
            video_ids.append(item["contentDetails"]["videoId"])

        if stop:
            break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return video_ids


async def fetch_recent_uploads(playlist_id: str, days: int = 7) -> list[str]:
    """Async wrapper for playlist fetch."""
    return await asyncio.to_thread(_fetch_recent_uploads_sync, playlist_id, days)


def _enrich_video_details_sync(video_ids: list[str]) -> list[VideoData]:
    """Fetch full video details in batches of 50. Costs 1 unit per batch."""
    youtube = _build_youtube()
    videos: list[VideoData] = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]

        if not quota_tracker.consume(1):
            logger.warning("Quota exhausted during video enrichment")
            break

        response = (
            youtube.videos()
            .list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            )
            .execute()
        )

        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            videos.append(
                VideoData(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                    view_count=int(stats["viewCount"]) if stats.get("viewCount") else None,
                    like_count=int(stats["likeCount"]) if stats.get("likeCount") else None,
                    comment_count_api=int(stats["commentCount"]) if stats.get("commentCount") else None,
                    description=snippet.get("description", ""),
                    tags=snippet.get("tags", []),
                    thumbnail_url=snippet.get("thumbnails", {})
                    .get("medium", {})
                    .get("url", ""),
                )
            )

    return videos


async def enrich_video_details(video_ids: list[str]) -> list[VideoData]:
    """Async wrapper for video enrichment."""
    return await asyncio.to_thread(_enrich_video_details_sync, video_ids)


def check_duplicates(video_ids: list[str]) -> set[str]:
    """Return set of video_ids that already exist in ChromaDB."""
    return get_existing_video_ids(video_ids)
