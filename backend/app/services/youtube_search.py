import asyncio
import logging

from googleapiclient.discovery import build

from app.config import settings
from app.models.schemas import VideoData
from app.utils.quota_tracker import quota_tracker

logger = logging.getLogger(__name__)


def _build_youtube():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def _search_sync(
    keyword: str, max_results: int, page_token: str | None = None
) -> tuple[list[VideoData], str | None]:
    """Synchronous YouTube search + metadata enrichment.

    Returns (videos, next_page_token).
    """
    youtube = _build_youtube()

    # search.list costs 100 quota units
    if not quota_tracker.consume(100):
        raise RuntimeError(
            f"YouTube API quota exhausted. Remaining: {quota_tracker.remaining}"
        )

    params = dict(
        q=keyword,
        part="id,snippet",
        type="video",
        maxResults=min(max_results, 50),
        relevanceLanguage="ko",
        order="relevance",
    )
    if page_token:
        params["pageToken"] = page_token

    search_response = youtube.search().list(**params).execute()

    next_page_token = search_response.get("nextPageToken")

    video_ids = [
        item["id"]["videoId"]
        for item in search_response.get("items", [])
        if item["id"].get("videoId")
    ]

    if not video_ids:
        return [], None

    # videos.list costs 1 quota unit per call
    if not quota_tracker.consume(1):
        raise RuntimeError("YouTube API quota exhausted for videos.list")

    details_response = (
        youtube.videos()
        .list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        )
        .execute()
    )

    videos = []
    for item in details_response.get("items", []):
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        videos.append(
            VideoData(
                video_id=item["id"],
                title=snippet.get("title", ""),
                channel_title=snippet.get("channelTitle", ""),
                published_at=snippet.get("publishedAt", ""),
                view_count=int(stats.get("viewCount", 0)) if stats.get("viewCount") else None,
                like_count=int(stats.get("likeCount", 0)) if stats.get("likeCount") else None,
                comment_count_api=int(stats.get("commentCount", 0)) if stats.get("commentCount") else None,
                description=snippet.get("description", ""),
                tags=snippet.get("tags", []),
                thumbnail_url=snippet.get("thumbnails", {})
                .get("medium", {})
                .get("url", ""),
            )
        )

    return videos, next_page_token


async def search_videos(
    keyword: str, max_results: int, page_token: str | None = None
) -> tuple[list[VideoData], str | None]:
    """Async wrapper for YouTube search. Returns (videos, next_page_token)."""
    return await asyncio.to_thread(_search_sync, keyword, max_results, page_token)
