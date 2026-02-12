from fastapi import APIRouter, Query

from app.services.vector_store import (
    get_comments_for_video,
    get_subtitles_for_video,
    get_video_data,
)

router = APIRouter()


@router.get("")
async def list_videos(run_id: str | None = Query(None)):
    videos = get_video_data(run_id)
    return {"videos": videos, "total": len(videos)}


@router.get("/{video_id}")
async def get_video(video_id: str):
    subtitles = get_subtitles_for_video(video_id)
    comments = get_comments_for_video(video_id)
    return {
        "video_id": video_id,
        "subtitles": subtitles,
        "comments": comments,
    }


@router.get("/{video_id}/subtitles")
async def get_subtitles(video_id: str):
    subtitles = get_subtitles_for_video(video_id)
    return {"video_id": video_id, "subtitles": subtitles}


@router.get("/{video_id}/comments")
async def get_comments(video_id: str):
    comments = get_comments_for_video(video_id)
    return {"video_id": video_id, "comments": comments}
