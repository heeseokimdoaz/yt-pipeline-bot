import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sse_starlette.sse import ServerSentEvent

from app.models.schemas import PipelineRequest, PipelineRunSummary
from app.services.comment_collector import collect_comments
from app.services.metadata_filter import filter_videos
from app.services.subtitle_extractor import extract_subtitles
from app.services.vector_store import store_comments, store_subtitles, store_videos
from app.services.youtube_search import search_videos

logger = logging.getLogger(__name__)

# In-memory pipeline state (demo-only)
pipeline_runs: dict[str, dict] = {}


async def start_pipeline(request: PipelineRequest) -> str:
    """Start a new pipeline run. Returns run_id."""
    run_id = str(uuid.uuid4())
    pipeline_runs[run_id] = {
        "status": "running",
        "events": asyncio.Queue(),
        "request": request,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "summary": PipelineRunSummary(
            run_id=run_id,
            keywords=request.keywords,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        ),
    }
    asyncio.create_task(_execute_pipeline(run_id, request))
    return run_id


async def stream_events(run_id: str) -> AsyncGenerator[ServerSentEvent, None]:
    """SSE generator that yields pipeline progress events."""
    if run_id not in pipeline_runs:
        yield ServerSentEvent(
            data=json.dumps({"error": "Pipeline run not found"}),
            event="pipeline_error",
        )
        return

    queue = pipeline_runs[run_id]["events"]
    while True:
        event = await queue.get()
        yield ServerSentEvent(
            data=json.dumps(event["data"], ensure_ascii=False),
            event=event["type"],
        )
        if event["type"] in ("pipeline_completed", "pipeline_error"):
            break


def get_run_summary(run_id: str) -> PipelineRunSummary | None:
    run = pipeline_runs.get(run_id)
    if not run:
        return None
    return run["summary"]


def get_all_runs() -> list[PipelineRunSummary]:
    return [r["summary"] for r in pipeline_runs.values()]


async def _emit(run_id: str, event_type: str, data: dict):
    """Push an event to the SSE queue."""
    queue = pipeline_runs[run_id]["events"]
    await queue.put({"type": event_type, "data": data})


async def _execute_pipeline(run_id: str, request: PipelineRequest):
    """Main pipeline execution logic."""
    summary = pipeline_runs[run_id]["summary"]
    total_subtitle_chunks = 0
    total_comments = 0

    try:
        # --- Step 1 & 2: Search + Filter loop ---
        has_filter = bool(request.filter_keywords or request.exclude_keywords)
        target = request.max_results
        max_pages = 5  # safety limit to avoid infinite pagination

        await _emit(run_id, "search_started", {
            "run_id": run_id,
            "keywords": request.keywords,
        })

        filtered: list = []
        seen: set[str] = set()
        total_searched = 0

        # Track page tokens per keyword
        page_tokens: dict[str, str | None] = {kw: None for kw in request.keywords}

        for page in range(max_pages):
            if len(filtered) >= target:
                break

            # Check if any keyword still has pages left
            active_keywords = [
                kw for kw in request.keywords
                if page_tokens.get(kw) is not None or page == 0
            ]
            if not active_keywords:
                break

            page_videos = []
            for keyword in active_keywords:
                batch_size = request.max_results * 5 if has_filter else request.max_results
                videos, next_token = await search_videos(
                    keyword, batch_size, page_tokens[keyword]
                )
                page_tokens[keyword] = next_token
                for v in videos:
                    if v.video_id not in seen:
                        seen.add(v.video_id)
                        page_videos.append(v)

                await _emit(run_id, "search_progress", {
                    "keyword": keyword,
                    "found": len(videos),
                    "page": page + 1,
                    "total_so_far": len(seen),
                })

            total_searched += len(page_videos)

            if has_filter:
                passed = filter_videos(
                    page_videos,
                    request.filter_keywords,
                    request.filter_mode,
                    exclude_keywords=request.exclude_keywords,
                )
                filtered.extend(passed)
            else:
                filtered.extend(page_videos)

            # If first page already fills target or no filter, no need to loop
            if not has_filter:
                break

        # Trim to target count
        filtered = filtered[:target]

        await _emit(run_id, "filter_progress", {
            "total_searched": total_searched,
            "passed": len(filtered),
            "filtered_out": total_searched - len(filtered),
        })

        # --- Step 3: Subtitles ---
        if request.include_subtitles:
            for i, video in enumerate(filtered):
                sub_result = await extract_subtitles(
                    video.video_id, request.subtitle_languages
                )
                status = "ok" if sub_result else "not_available"
                sub_chunks = 0

                if sub_result:
                    sub_chunks = store_subtitles(sub_result, run_id)
                    total_subtitle_chunks += sub_chunks

                await _emit(run_id, "subtitle_progress", {
                    "video_id": video.video_id,
                    "title": video.title,
                    "status": status,
                    "chunks": sub_chunks,
                    "progress": f"{i + 1}/{len(filtered)}",
                })

        # --- Step 4: Comments ---
        if request.include_comments:
            for i, video in enumerate(filtered):
                comments = await collect_comments(
                    video.video_id, request.max_comments_per_video
                )
                comment_count = 0
                if comments:
                    comment_count = store_comments(comments, video.video_id, run_id)
                    total_comments += comment_count

                await _emit(run_id, "comment_progress", {
                    "video_id": video.video_id,
                    "title": video.title,
                    "count": comment_count,
                    "progress": f"{i + 1}/{len(filtered)}",
                })

        # --- Step 5: Store video metadata ---
        video_count = store_videos(filtered, run_id)
        await _emit(run_id, "storage_progress", {
            "videos_stored": video_count,
            "subtitle_chunks_stored": total_subtitle_chunks,
            "comments_stored": total_comments,
        })

        # --- Done ---
        summary.status = "completed"
        summary.video_count = video_count
        summary.subtitle_count = total_subtitle_chunks
        summary.comment_count = total_comments

        await _emit(run_id, "pipeline_completed", {
            "run_id": run_id,
            "video_count": video_count,
            "subtitle_chunks": total_subtitle_chunks,
            "comment_count": total_comments,
        })

    except Exception as e:
        logger.exception("Pipeline %s failed", run_id)
        summary.status = "error"
        await _emit(run_id, "pipeline_error", {
            "run_id": run_id,
            "error": str(e),
        })
