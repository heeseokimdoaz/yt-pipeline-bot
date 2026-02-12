import logging
from typing import Literal

from app.models.schemas import VideoData

logger = logging.getLogger(__name__)


def filter_videos(
    videos: list[VideoData],
    filter_keywords: list[str],
    mode: Literal["any", "all"] = "any",
    exclude_keywords: list[str] | None = None,
) -> list[VideoData]:
    """Filter videos by checking if keywords appear in title, description, or tags.

    mode="any": keep video if ANY filter keyword is found
    mode="all": keep video if ALL filter keywords are found
    exclude_keywords: remove video if ANY exclude keyword is found
    """
    result = videos

    # --- Inclusion filter ---
    if filter_keywords:
        included = []
        for video in result:
            searchable = (
                f"{video.title} {video.description} {' '.join(video.tags)}"
            ).lower()

            matches = [kw.lower() in searchable for kw in filter_keywords]

            if mode == "any" and any(matches):
                included.append(video)
            elif mode == "all" and all(matches):
                included.append(video)

        logger.info(
            "Inclusion filter: %d -> %d videos (mode=%s, keywords=%s)",
            len(result),
            len(included),
            mode,
            filter_keywords,
        )
        result = included

    # --- Exclusion filter ---
    if exclude_keywords:
        before = len(result)
        excluded = []
        for video in result:
            searchable = (
                f"{video.title} {video.description} {' '.join(video.tags)}"
            ).lower()

            if not any(kw.lower() in searchable for kw in exclude_keywords):
                excluded.append(video)

        logger.info(
            "Exclusion filter: %d -> %d videos (exclude_keywords=%s)",
            before,
            len(excluded),
            exclude_keywords,
        )
        result = excluded

    return result
