import logging
from typing import Literal

from app.models.schemas import VideoData

logger = logging.getLogger(__name__)


def filter_videos(
    videos: list[VideoData],
    filter_keywords: list[str],
    mode: Literal["any", "all"] = "any",
) -> list[VideoData]:
    """Filter videos by checking if keywords appear in title, description, or tags.

    mode="any": keep video if ANY filter keyword is found
    mode="all": keep video if ALL filter keywords are found
    """
    if not filter_keywords:
        return videos

    filtered = []
    for video in videos:
        searchable = (
            f"{video.title} {video.description} {' '.join(video.tags)}"
        ).lower()

        matches = [kw.lower() in searchable for kw in filter_keywords]

        if mode == "any" and any(matches):
            filtered.append(video)
        elif mode == "all" and all(matches):
            filtered.append(video)

    logger.info(
        "Filtered %d -> %d videos (mode=%s, keywords=%s)",
        len(videos),
        len(filtered),
        mode,
        filter_keywords,
    )
    return filtered
