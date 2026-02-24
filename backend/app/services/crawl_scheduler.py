import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.models.channel_schemas import ChannelCrawlResult, CrawlRunSummary
from app.services.channel_crawler import (
    check_duplicates,
    enrich_video_details,
    fetch_recent_uploads,
    get_enabled_channels,
)
from app.services.comment_collector import collect_comments
from app.services.subtitle_extractor import extract_subtitles
from app.services.vector_store import (
    get_all_video_ids,
    get_video_ids_with_comments,
    get_video_ids_with_subtitles,
    store_comments,
    store_subtitles,
    store_videos,
)
from app.utils.quota_tracker import quota_tracker

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# In-memory crawl state
crawl_runs: dict[str, CrawlRunSummary] = {}
_crawl_lock = asyncio.Lock()


async def execute_daily_crawl() -> str:
    """Main orchestration: crawl all enabled channels for recent videos."""
    if _crawl_lock.locked():
        logger.warning("Crawl already in progress, skipping.")
        return ""

    async with _crawl_lock:
        run_id = f"crawl-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        channels = get_enabled_channels()

        summary = CrawlRunSummary(
            run_id=run_id,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            channels_total=len(channels),
        )
        crawl_runs[run_id] = summary

        logger.info("Crawl %s started: %d channels", run_id, len(channels))

        # Check quota reserve
        if quota_tracker.remaining < settings.crawl_min_quota_reserve:
            summary.status = "error"
            summary.errors.append({
                "type": "quota_reserve",
                "message": f"Insufficient quota: {quota_tracker.remaining} < {settings.crawl_min_quota_reserve}",
            })
            summary.completed_at = datetime.now(timezone.utc).isoformat()
            logger.warning("Crawl skipped: insufficient quota (%d)", quota_tracker.remaining)
            return run_id

        for channel in channels:
            result = await _crawl_single_channel(channel, run_id)
            summary.channels_processed += 1
            summary.new_videos_found += result.new_videos
            summary.videos_skipped_duplicate += result.skipped_videos
            summary.subtitles_collected += result.subtitles_collected
            summary.comments_collected += result.comments_collected

            if result.error:
                summary.errors.append({
                    "channel": channel.channel_name,
                    "error": result.error,
                })

            # Abort if quota is critically low
            if quota_tracker.remaining < 100:
                logger.warning("Quota critically low (%d), stopping crawl", quota_tracker.remaining)
                summary.errors.append({
                    "type": "quota_exhausted",
                    "message": f"Stopped early: quota at {quota_tracker.remaining}",
                })
                break

        summary.status = "completed" if not summary.errors else "completed_with_errors"
        summary.completed_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Crawl %s done: %d new videos, %d skipped, %d subtitles, %d comments, %d errors",
            run_id,
            summary.new_videos_found,
            summary.videos_skipped_duplicate,
            summary.subtitles_collected,
            summary.comments_collected,
            len(summary.errors),
        )
        return run_id


async def _crawl_single_channel(channel, run_id: str) -> ChannelCrawlResult:
    """Crawl a single channel: fetch uploads, dedup, enrich, store."""
    result = ChannelCrawlResult(
        channel_id=channel.channel_id,
        channel_name=channel.channel_name,
        category=channel.category,
    )

    try:
        # 1. Fetch recent uploads
        video_ids = await fetch_recent_uploads(
            channel.uploads_playlist_id, settings.crawl_days_back
        )
        logger.info(
            "[%s] Found %d recent videos", channel.channel_name, len(video_ids)
        )

        if not video_ids:
            return result

        # 2. Dedup
        existing = check_duplicates(video_ids)
        new_ids = [vid for vid in video_ids if vid not in existing]
        result.skipped_videos = len(existing & set(video_ids))

        if not new_ids:
            logger.info("[%s] All videos already crawled", channel.channel_name)
            return result

        # 3. Enrich new videos
        videos = await enrich_video_details(new_ids)

        # Attach category
        for v in videos:
            v.channel_category = channel.category

        # 4. Store video metadata
        store_videos(videos, run_id)
        result.new_videos = len(videos)

        # 5. Subtitles + Comments for each new video
        for video in videos:
            # Subtitles
            sub_result = await extract_subtitles(
                video.video_id, settings.crawl_subtitle_languages
            )
            if sub_result:
                chunks = store_subtitles(sub_result, run_id)
                result.subtitles_collected += chunks

            # Comments
            comments = await collect_comments(
                video.video_id, settings.crawl_max_comments_per_video
            )
            if comments:
                count = store_comments(comments, video.video_id, run_id)
                result.comments_collected += count

        logger.info(
            "[%s] Done: %d new, %d subtitles, %d comments",
            channel.channel_name,
            result.new_videos,
            result.subtitles_collected,
            result.comments_collected,
        )

    except Exception as e:
        logger.exception("[%s] Crawl failed", channel.channel_name)
        result.error = str(e)

    return result


async def reprocess_missing() -> dict:
    """Re-process existing videos that are missing subtitles or comments."""
    all_ids = get_all_video_ids()
    has_subs = get_video_ids_with_subtitles()
    has_comments = get_video_ids_with_comments()

    missing_subs = [vid for vid in all_ids if vid not in has_subs]
    missing_comments = [vid for vid in all_ids if vid not in has_comments]

    logger.info(
        "Reprocess: %d videos missing subtitles, %d missing comments",
        len(missing_subs),
        len(missing_comments),
    )

    subs_added = 0
    comments_added = 0

    # Re-extract subtitles
    for i, video_id in enumerate(missing_subs):
        try:
            sub_result = await extract_subtitles(
                video_id, settings.crawl_subtitle_languages
            )
            if sub_result:
                chunks = store_subtitles(sub_result, "reprocess")
                subs_added += chunks
                logger.info(
                    "  [%d/%d] Subtitles for %s: %d chunks",
                    i + 1, len(missing_subs), video_id, chunks,
                )
            else:
                logger.info(
                    "  [%d/%d] No subtitles for %s",
                    i + 1, len(missing_subs), video_id,
                )
        except Exception as e:
            logger.warning("Subtitle reprocess failed for %s: %s", video_id, e)

    # Re-collect comments
    for i, video_id in enumerate(missing_comments):
        if quota_tracker.remaining < 100:
            logger.warning("Quota low, stopping comment reprocess")
            break
        try:
            comments = await collect_comments(
                video_id, settings.crawl_max_comments_per_video
            )
            if comments:
                count = store_comments(comments, video_id, "reprocess")
                comments_added += count
                logger.info(
                    "  [%d/%d] Comments for %s: %d",
                    i + 1, len(missing_comments), video_id, count,
                )
        except Exception as e:
            logger.warning("Comment reprocess failed for %s: %s", video_id, e)

    result = {
        "total_videos": len(all_ids),
        "missing_subtitles": len(missing_subs),
        "missing_comments": len(missing_comments),
        "subtitles_added": subs_added,
        "comments_added": comments_added,
    }
    logger.info("Reprocess complete: %s", result)
    return result


# --- Scheduler lifecycle ---


def start_scheduler():
    """Start the APScheduler with daily crawl job."""
    if not settings.crawl_enabled:
        logger.info("Crawler disabled via CRAWL_ENABLED=false")
        return

    scheduler.add_job(
        execute_daily_crawl,
        trigger=CronTrigger(hour=settings.crawl_hour_utc, minute=settings.crawl_minute),
        id="daily_crawl",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: daily crawl at %02d:%02d UTC",
        settings.crawl_hour_utc,
        settings.crawl_minute,
    )


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


# --- Query functions ---


def get_crawl_status(run_id: str) -> CrawlRunSummary | None:
    return crawl_runs.get(run_id)


def get_crawl_history() -> list[CrawlRunSummary]:
    return list(crawl_runs.values())


def get_schedule_info() -> dict:
    job = scheduler.get_job("daily_crawl")
    return {
        "enabled": settings.crawl_enabled,
        "scheduler_running": scheduler.running,
        "next_run": str(job.next_run_time) if job else None,
        "cron": f"{settings.crawl_hour_utc:02d}:{settings.crawl_minute:02d} UTC",
        "days_back": settings.crawl_days_back,
        "channels_configured": len(get_enabled_channels()),
    }
