import asyncio
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.models.schemas import CommentData
from app.utils.quota_tracker import quota_tracker

logger = logging.getLogger(__name__)


def _collect_sync(video_id: str, max_comments: int) -> list[CommentData]:
    """Synchronous comment collection with pagination."""
    youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
    comments: list[CommentData] = []
    page_token = None

    while len(comments) < max_comments:
        if not quota_tracker.consume(1):
            logger.warning("Quota exhausted during comment collection")
            break

        try:
            response = (
                youtube.commentThreads()
                .list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),
                    pageToken=page_token,
                    order="relevance",
                    textFormat="plainText",
                )
                .execute()
            )
        except HttpError as e:
            if e.resp.status == 403:
                logger.warning("Comments disabled for %s", video_id)
                break
            raise

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append(
                CommentData(
                    comment_id=item["id"],
                    author=top["authorDisplayName"],
                    text=top["textDisplay"],
                    like_count=top.get("likeCount", 0),
                    published_at=top["publishedAt"],
                    is_reply=False,
                )
            )

            if "replies" in item:
                for reply in item["replies"]["comments"]:
                    r = reply["snippet"]
                    comments.append(
                        CommentData(
                            comment_id=reply["id"],
                            author=r["authorDisplayName"],
                            text=r["textDisplay"],
                            like_count=r.get("likeCount", 0),
                            published_at=r["publishedAt"],
                            is_reply=True,
                        )
                    )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments[:max_comments]


async def collect_comments(
    video_id: str, max_comments: int = 100
) -> list[CommentData]:
    """Async wrapper for comment collection."""
    return await asyncio.to_thread(_collect_sync, video_id, max_comments)
