from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import PipelineRequest, PipelineResponse, PipelineRunSummary
from app.services.pipeline_runner import (
    get_all_runs,
    get_run_summary,
    start_pipeline,
    stream_events,
)
from app.utils.quota_tracker import quota_tracker

router = APIRouter()


@router.post("/run", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest):
    if not request.keywords:
        raise HTTPException(status_code=400, detail="At least one keyword is required")

    run_id = await start_pipeline(request)
    return PipelineResponse(
        run_id=run_id,
        status="started",
        sse_url=f"/api/pipeline/status/{run_id}",
    )


@router.get("/status/{run_id}")
async def pipeline_status(run_id: str):
    return EventSourceResponse(stream_events(run_id))


@router.get("/history", response_model=list[PipelineRunSummary])
async def pipeline_history():
    return get_all_runs()


@router.get("/quota")
async def get_quota():
    return {
        "remaining": quota_tracker.remaining,
        "daily_limit": quota_tracker.daily_limit,
        "used": quota_tracker.used,
    }
